const base=import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8001'
async function request(path,options={}){const r=await fetch(`${base}${path}`,{headers:{'Content-Type':'application/json'},...options});const body=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(body.detail||`Request failed (${r.status})`),{status:r.status});return body}
export const api={health:()=>request('/health'),documents:()=>request('/documents'),metrics:()=>request('/metrics'),chat:(question,context='')=>request('/chat',{method:'POST',body:JSON.stringify({question,context})})}
