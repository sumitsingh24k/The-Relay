"""Public API for the frontend; metrics remain empty until real runs."""
import asyncio, json, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import GroqClient, StandInClient
from pipeline import DailyProviderBudgetError, retrieval_only_fallback, run_pipeline
from retrieve import BM25Retriever
from metrics import append_result, read_rows
from analysis.analyze import summarize
from scheduler import AdmissionError, Scheduler, config_from_env
BASE=Path(__file__).resolve().parent
SCHEDULER=Scheduler(config_from_env())
@asynccontextmanager
async def lifespan(_app):
 await SCHEDULER.start()
 try: yield
 finally: await SCHEDULER.stop()
app=FastAPI(title="Relay", lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_methods=["*"],allow_headers=["*"])
class ChatRequest(BaseModel): question:str; context:str=""; source:str="groq"; retrieval_setting:str="B-medium"; scenario:str="interactive"
class QuotaTrackedClient:
 def __init__(self, client, deadline: float, estimated_tokens: int=1000): self.client,self.deadline,self.estimated_tokens=client,deadline,estimated_tokens
 async def generate(self,messages):
  await SCHEDULER.admit(self.estimated_tokens,self.deadline)
  result=await self.client.generate(messages)
  actual=(result.tokens_in or 0)+(result.tokens_out or 0)
  await SCHEDULER.reconcile_tokens(self.estimated_tokens,actual if actual else None)
  return result
@app.get('/health')
def health(): return {"backend":"healthy","retrieval":"ready","scheduler":SCHEDULER.mode(),"groq":"configured","standin":"not_checked","queue_depth":SCHEDULER.queue.qsize(),"peak_queue_length":SCHEDULER.peak_queue_length,"scheduler_config":SCHEDULER.config.__dict__,"daily_usage":{"requests":SCHEDULER._daily_requests,"estimated_tokens":SCHEDULER._daily_tokens}}
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
 request_id=f"api-error-{int(time.time()*1000)}"
 try:
  deadline=time.monotonic()+30
  # Resolve short follow-ups ("where can I use this?") using only the preceding user topic.
  effective_question = f"Previous topic: {r.context}\nFollow-up: {r.question}" if r.context.strip() else r.question
  # Pressure mode skips semantic re-ranking and retrieves fewer passages while retaining verification.
  selected_setting = "A-small" if SCHEDULER.mode() == "pressured" else r.retrieval_setting
  async def work():
   provider=StandInClient() if r.source=='standin' else GroqClient()
   return await run_pipeline(effective_question,QuotaTrackedClient(provider,deadline),BM25Retriever(),selected_setting)
  result=await SCHEDULER.submit(work,deadline)
  append_result(result,scenario=r.scenario,source=r.source)
  return result
 except DailyProviderBudgetError:
  started=time.perf_counter(); retriever=BM25Retriever(); chunks=retriever.retrieve_passages(r.question,r.retrieval_setting)
  result=retrieval_only_fallback(r.question,chunks,f"fallback-{int(time.time()*1000)}")
  elapsed=round((time.perf_counter()-started)*1000,3); result["timing_ms"]={"model_ttft":None,"user_visible_ttft":elapsed,"total":elapsed,"model_total":None}; result["retrieval_setting"]=r.retrieval_setting; result["retries"]=0
  append_result(result,scenario=r.scenario,source="retrieval_only")
  return result
 except AdmissionError as e:
  if e.code == 'daily_budget':
   started=time.perf_counter(); retriever=BM25Retriever(); chunks=retriever.retrieve_passages(r.question,r.retrieval_setting)
   result=retrieval_only_fallback(r.question,chunks,f"fallback-{int(time.time()*1000)}")
   elapsed=round((time.perf_counter()-started)*1000,3); result["timing_ms"]={"model_ttft":None,"user_visible_ttft":elapsed,"total":elapsed,"model_total":None}; result["retrieval_setting"]=r.retrieval_setting; result["retries"]=0
   append_result(result,scenario=r.scenario,source='retrieval_only')
   return result
  status=429 if e.code in {'minute_budget','daily_budget','queue_full'} else 408
  append_result({"request_id":request_id,"status":"rate_limited" if status == 429 else "timeout","timing_ms":{},"usage":{},"retries":0,"retrieval_setting":r.retrieval_setting},scenario=r.scenario,source=r.source)
  raise HTTPException(status,e.args[0]) from e
 except RuntimeError as e:
  provider_status=getattr(e,'status_code',None)
  status=429 if provider_status == 429 else 503
  append_result({"request_id":request_id,"status":"rate_limited" if status == 429 else "error","timing_ms":{},"usage":{},"retries":getattr(e,'relay_retries',0),"retry_wait_ms":getattr(e,'relay_retry_wait_ms',0),"scheduler_timing_ms":getattr(e,'scheduler_timing_ms',None),"retrieval_setting":r.retrieval_setting},scenario=r.scenario,source=r.source)
  raise HTTPException(status,str(e)) from e
 except ValueError as e:
  append_result({"request_id":request_id,"status":"error","timing_ms":{},"usage":{},"retries":0,"retrieval_setting":r.retrieval_setting},scenario=r.scenario,source=r.source)
  raise HTTPException(400,str(e)) from e
