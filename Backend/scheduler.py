"""Single-process admission, quota and retry policy for Relay requests."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class SchedulerConfig:
    rpm: int = 30
    tpm: int = 6_000
    daily_requests: int = 500
    daily_tokens: int = 100_000
    max_queue: int = 30
    max_concurrency: int = 4
    max_retries: int = 2
    base_backoff_s: float = 0.25


class AdmissionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class QueuedWork:
    work: Callable[[], Awaitable]
    deadline_monotonic: float
    future: asyncio.Future


class Scheduler:
    def __init__(self, config: SchedulerConfig = SchedulerConfig()) -> None:
        self.config = config
        self.queue: asyncio.Queue[object] = asyncio.Queue(maxsize=config.max_queue)
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self._lock = asyncio.Lock()
        self._minute_start = time.monotonic()
        self._requests_this_minute = 0
        self._tokens_this_minute = 0
        self._daily_requests = 0
        self._daily_tokens = 0
        self.peak_queue_length = 0
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        if not self._workers:
            self._workers = [asyncio.create_task(self._worker(), name=f"relay-worker-{index}") for index in range(self.config.max_concurrency)]

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def submit(self, work: Callable[[], Awaitable], deadline_monotonic: float):
        if time.monotonic() >= deadline_monotonic:
            raise AdmissionError("deadline", "request expired before queueing")
        if self.queue.full():
            raise AdmissionError("queue_full", "bounded queue is full")
        future = asyncio.get_running_loop().create_future()
        self.queue.put_nowait(QueuedWork(work, deadline_monotonic, future))
        self.peak_queue_length = max(self.peak_queue_length, self.queue.qsize())
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=max(0.001, deadline_monotonic - time.monotonic()))
        except TimeoutError as error:
            if not future.done():
                future.cancel()
            raise AdmissionError("deadline", "request expired while queued") from error

    async def _worker(self) -> None:
        while True:
            job: QueuedWork = await self.queue.get()
            try:
                if job.future.cancelled():
                    continue
                result = await self.execute(job.work, job.deadline_monotonic)
                if not job.future.done():
                    job.future.set_result(result)
            except Exception as error:
                if not job.future.done():
                    job.future.set_exception(error)
            finally:
                self.queue.task_done()

    async def admit(self, estimated_tokens: int, deadline_monotonic: float) -> None:
        """Reserve quota before a model call; caller is responsible for executing work after admission."""
        if estimated_tokens <= 0:
            raise ValueError("estimated_tokens must be positive")
        if time.monotonic() >= deadline_monotonic:
            raise AdmissionError("deadline", "request expired before admission")
        async with self._lock:
            now = time.monotonic()
            if now - self._minute_start >= 60:
                self._minute_start, self._requests_this_minute, self._tokens_this_minute = now, 0, 0
            if self._daily_requests >= self.config.daily_requests or self._daily_tokens + estimated_tokens > self.config.daily_tokens:
                raise AdmissionError("daily_budget", "daily provider budget exhausted; use retrieval-only fallback")
            if self._requests_this_minute >= self.config.rpm or self._tokens_this_minute + estimated_tokens > self.config.tpm:
                raise AdmissionError("minute_budget", "RPM or TPM budget unavailable; wait or degrade")
            self._requests_this_minute += 1
            self._tokens_this_minute += estimated_tokens
            self._daily_requests += 1
            self._daily_tokens += estimated_tokens

    async def enqueue(self, item: object, deadline_monotonic: float) -> None:
        if self.queue.full():
            raise AdmissionError("queue_full", "bounded queue is full")
        if time.monotonic() >= deadline_monotonic:
            raise AdmissionError("deadline", "request expired while waiting")
        self.queue.put_nowait(item)
        self.peak_queue_length = max(self.peak_queue_length, self.queue.qsize())

    async def execute(self, work, deadline_monotonic: float):
        """Run one admitted coroutine under concurrency and deadline control."""
        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise AdmissionError("deadline", "request expired before execution")
        async with self.semaphore:
            try:
                return await asyncio.wait_for(work(), timeout=remaining)
            except TimeoutError as error:
                raise AdmissionError("deadline", "request deadline exceeded during execution") from error

    async def retry_delay(self, retry_index: int, retry_after_s: float | None = None) -> float:
        if retry_index >= self.config.max_retries:
            raise AdmissionError("retry_exhausted", "bounded retry budget exhausted")
        exponential = self.config.base_backoff_s * (2**retry_index)
        delay = max(exponential, retry_after_s or 0)
        return delay + random.uniform(0, delay * 0.25)

    def mode(self) -> str:
        """Normal: full pipeline; pressured: cheap safe path; budget_gone: retrieval-only."""
        if self._daily_requests >= self.config.daily_requests or self._daily_tokens >= self.config.daily_tokens:
            return "budget_gone"
        if self.queue.qsize() / self.config.max_queue >= 0.7 or self._requests_this_minute / self.config.rpm >= 0.7:
            return "pressured"
        return "normal"
