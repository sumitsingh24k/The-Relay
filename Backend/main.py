"""Public API for the frontend; metrics remain empty until real runs."""
import asyncio, json, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import GroqClient, StandInClient
from pipeline import retrieval_only_fallback, run_pipeline
from retrieve import BM25Retriever
from metrics import append_result, read_rows
from analysis.analyze import summarize
from scheduler import AdmissionError, Scheduler
BASE=Path(__file__).resolve().parent
SCHEDULER=Scheduler()
@asynccontextmanager
async def lifespan(_app):
 await SCHEDULER.start()
 try: yield
 finally: await SCHEDULER.stop()
app=FastAPI(title="Relay", lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_methods=["*"],allow_headers=["*"])
class ChatRequest(BaseModel): question:str; context:str=""; source:str="groq"; retrieval_setting:str="B-medium"
@app.get('/health')
def health(): return {"backend":"healthy","retrieval":"ready","scheduler":SCHEDULER.mode(),"groq":"configured","standin":"not_checked","queue_depth":SCHEDULER.queue.qsize(),"peak_queue_length":SCHEDULER.peak_queue_length}
@app.get('/documents')
def documents():
 p=BASE/'data/papers/manifest.json';return {"documents":json.loads(p.read_text(encoding='utf-8'))['verified_papers'] if p.exists() else []}
@app.get('/results')
def results():
 return {"rows":read_rows()}
@app.get('/metrics')
def metrics():
 rows=read_rows();return {"sample_count":len(rows),"metrics":summarize(rows),"note":"No measurements are available until actual requests or load tests are run." if not rows else None}
@app.post('/chat')
async def chat(r:ChatRequest):
 try:
  deadline=time.monotonic()+30
  await SCHEDULER.admit(estimated_tokens=1000,deadline_monotonic=deadline)
  # Resolve short follow-ups ("where can I use this?") using only the preceding user topic.
  effective_question = f"Previous topic: {r.context}\nFollow-up: {r.question}" if r.context.strip() else r.question
  async def work(): return await run_pipeline(effective_question,StandInClient() if r.source=='standin' else GroqClient(),BM25Retriever(),r.retrieval_setting)
  result=await SCHEDULER.submit(work,deadline)
  append_result(result,scenario='interactive',source=r.source)
  return result
 except AdmissionError as e:
  if e.code == 'daily_budget':
   started=time.perf_counter(); retriever=BM25Retriever(); chunks=retriever.retrieve_passages(r.question,r.retrieval_setting)
   result=retrieval_only_fallback(r.question,chunks,f"fallback-{int(time.time()*1000)}")
   elapsed=round((time.perf_counter()-started)*1000,3); result["timing_ms"]={"model_ttft":None,"user_visible_ttft":elapsed,"total":elapsed,"model_total":None}; result["retrieval_setting"]=r.retrieval_setting; result["retries"]=0
   append_result(result,scenario='interactive',source='retrieval_only')
   return result
  status=429 if e.code in {'minute_budget','daily_budget','queue_full'} else 408
  raise HTTPException(status,e.args[0]) from e
 except RuntimeError as e:raise HTTPException(503,str(e)) from e
 except ValueError as e:raise HTTPException(400,str(e)) from e
