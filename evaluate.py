"""Run a user-configured chat-completions-compatible API, or score saved runs.

Credentials are environment-only. This script makes no API calls unless `run` is used.
"""
import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parent
SYSTEM='Answer the spatial question using only the supplied context. Return a JSON object with exactly one key, "answer". Its value must be a boolean or array of feature IDs as requested. Do not include explanations, SQL, or markdown.'

def load(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]

def prompt(q):
    # Deliberately exclude SQL, fixture_expected, and the answer key.
    return json.dumps({'question':q['question'],'context':q['context']},ensure_ascii=False)

def valid_answer(value,kind):
    if kind=='boolean': return type(value) is bool
    return isinstance(value,list) and all(isinstance(x,str) for x in value) and len(value)==len(set(value))

def correct(actual,expected,kind):
    if not valid_answer(actual,kind): return False
    return set(actual)==set(expected) if kind=='set' else actual==expected

def run(args):
    key=os.environ.get('MODEL_API_KEY')
    if not key: raise SystemExit('Set MODEL_API_KEY in your environment; never commit it.')
    if not args.endpoint.startswith('https://'): raise SystemExit('An HTTPS endpoint is required.')
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    questions=load(ROOT/'questions.jsonl')
    if args.limit: questions=questions[:args.limit]
    done={}
    if out.exists():
        for row in load(out):
            if row['requested_model']!=args.model or row['endpoint']!=args.endpoint or row['temperature']!=args.temperature:
                raise SystemExit('Output belongs to a different model/configuration; choose a new output file.')
            done[row['id']]=row
    for q in questions:
        user=prompt(q); digest=hashlib.sha256((SYSTEM+'\n'+user).encode()).hexdigest()
        if q['id'] in done:
            if done[q['id']]['prompt_sha256']!=digest: raise SystemExit('Inputs changed; choose a new output file.')
            continue
        payload={'model':args.model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':user}],
                 'temperature':args.temperature,'max_tokens':1024}
        row={'id':q['id'],'task':q['task'],'requested_model':args.model,'endpoint':args.endpoint,
             'timestamp_utc':datetime.now(timezone.utc).isoformat(),'temperature':args.temperature,
             'system_prompt':SYSTEM,'user_prompt':user,'prompt_sha256':digest}
        start=time.perf_counter()
        try:
            req=Request(args.endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
            with urlopen(req,timeout=180) as response: row['response']=json.load(response)
            row['status']='ok'
        except HTTPError as e:
            # No headers or credentials are saved; no silent retries.
            row.update(status='error',error=f'HTTP {e.code}')
        except Exception as e: row.update(status='error',error=type(e).__name__)
        row['latency_s']=time.perf_counter()-start
        with out.open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
        print(q['id'],row['status'])
        time.sleep(args.delay)

def score(args):
    truth={r['id']:r for r in load(ROOT/'answer_key.jsonl')}
    inputs={q['id']:q for q in load(ROOT/'questions.jsonl')}
    runs=load(args.input); seen=set(); rows=[]
    for r in runs:
        if r['id'] in seen or r['id'] not in truth: raise ValueError('Duplicate or unknown question ID')
        seen.add(r['id']); q=truth[r['id']]; actual=None; status=r['status']
        if status=='ok':
            expected_hash=hashlib.sha256((SYSTEM+'\n'+prompt(inputs[r['id']])).encode()).hexdigest()
            if r['prompt_sha256']!=expected_hash: raise ValueError('Prompt mismatch')
            try:
                decoded=json.loads(r['response']['choices'][0]['message']['content'])
                if set(decoded)!= {'answer'}: raise ValueError('Schema mismatch')
                actual=decoded['answer']
                status='valid' if valid_answer(actual,q['answer_type']) else 'invalid_schema'
            except (KeyError,IndexError,TypeError,ValueError): status='invalid_response'
        rows.append({'id':r['id'],'task':q['task'],'model':r['requested_model'],'status':status,
                     'expected_json':json.dumps(q['answer']),'actual_json':json.dumps(actual),
                     'correct':int(status=='valid' and correct(actual,q['answer'],q['answer_type'])),
                     'latency_s':r['latency_s']})
    with Path(args.output).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['id','task','model','status','expected_json','actual_json','correct','latency_s']); w.writeheader(); w.writerows(rows)
    print(f'Scored {len(rows)}/{len(truth)} questions. Omitted questions are NOT silently treated as evaluated; a full run requires 240 unique IDs.')

if __name__=='__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run'); r.add_argument('--endpoint',required=True,help='Full HTTPS chat/completions endpoint'); r.add_argument('--model',required=True)
    r.add_argument('--output',required=True); r.add_argument('--limit',type=int,default=0); r.add_argument('--delay',type=float,default=1); r.add_argument('--temperature',type=float,default=0)
    s=sub.add_parser('score'); s.add_argument('--input',required=True); s.add_argument('--output',default='model_results.csv')
    args=p.parse_args(); run(args) if args.command=='run' else score(args)
