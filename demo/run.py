"""One-command local stack, recording and render orchestration."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for d in ['work','raw','final','logs']:
    (ROOT/'demo'/d).mkdir(exist_ok=True)
def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)

def finish():
    run([sys.executable,'demo/render.py'])
    run([sys.executable,'demo/validate.py'])
    run([shutil.which('node'),'demo/player-check.cjs'])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render-only',action='store_true')
    parser.add_argument('--capture-only',action='store_true')
    args=parser.parse_args()
    if args.render_only:
        finish(); return
    stored=dotenv_values('.env')
    env=os.environ.copy()
    for k in ['GROQ_API_KEY','OPENROUTER_API_KEY','LLM_PROVIDER','LLM_MODEL']:
        if stored.get(k): env[k]=stored[k]
    if not env.get('GROQ_API_KEY') and not env.get('OPENROUTER_API_KEY'):
        raise RuntimeError('An LLM provider key is needed for real treatment-case reasoning.')
    test_key=stored.get('RAZORPAY_KEY_ID','')
    if test_key and not test_key.startswith('rzp_test_'):
        raise RuntimeError('Only Razorpay TEST MODE is allowed.')
    env.update({
        'DATABASE_URL':f'sqlite+aiosqlite:///./demo/work/demo-{uuid.uuid4().hex[:8]}.db',
        'REDIS_URL':'redis://127.0.0.1:6389/0', 'APP_ENV':'demo',
        'RAZORPAY_KEY_ID':test_key,'RAZORPAY_KEY_SECRET':stored.get('RAZORPAY_KEY_SECRET',''),
        'RAZORPAY_WEBHOOK_SECRET':uuid.uuid4().hex,'N8N_APPROVAL_WEBHOOK_URL':'',
        'NEXT_PUBLIC_API_URL':'http://127.0.0.1:8010','PYTHONUNBUFFERED':'1',
        'PYTHONPATH':str(ROOT),'PYTHONIOENCODING':'utf-8','NEXT_TELEMETRY_DISABLED':'1',
    })
    # An existing container is inspected, never deleted or reset.
    name='revenueguard-film-redis-'+uuid.uuid4().hex[:6]
    run(['docker','run','-d','--name',name,'-p','127.0.0.1:6389:6379','redis:7-alpine'])
    processes=[]; handles=[]
    try:
        def start(label,cmd,cwd=ROOT):
            handle=open(ROOT/'demo/logs'/f'{label}.log','w',encoding='utf-8'); handles.append(handle)
            p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=handle,stderr=handle,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)); processes.append(p)
            return p
        start('api',[sys.executable,'-m','uvicorn','demo.serve:app','--host','127.0.0.1','--port','8010'])
        start('worker',[sys.executable,'-m','backend.worker'])
        node=shutil.which('node')
        start('frontend',[node,'node_modules/next/dist/bin/next','dev','-p','3010'],ROOT/'frontend')
        with httpx.Client(timeout=60) as client:
            for url in ['http://127.0.0.1:8010/api/health','http://127.0.0.1:3010']:
                for attempt in range(90):
                    try:
                        if client.get(url).status_code==200: break
                    except httpx.HTTPError: pass
                    time.sleep(1)
                else: raise RuntimeError('Service failed to start; inspect local diagnostics')
            client.post('http://127.0.0.1:8010/demo/seed-health').raise_for_status()
        (ROOT/'demo/logs/environment.json').write_text(json.dumps({
            'database':'isolated SQLite','redis':'dedicated local Redis','worker':'actual backend.worker',
            'razorpay_test_credentials_present':bool(test_key),'llm_key_present':True,
            'external_downtime':'actual SDK; local synthetic telemetry drives outage',
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        },indent=2))
        run([node,'demo/record.cjs'],env=env)
    finally:
        for p in reversed(processes):
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill()
        for h in handles:h.close()
        # Stop only the new container created above; retained for recovery.
        subprocess.run(['docker','stop',name],stdout=subprocess.DEVNULL)
    if not args.capture_only:finish()

if __name__=='__main__':main()
