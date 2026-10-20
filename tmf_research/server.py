"""Loopback-only desktop research workbench; not a hosted tenant service."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
import uuid
import signal
from types import SimpleNamespace
from urllib.parse import urlsplit

from .engine import ResearchEngine, RunStore, brief, LENSES, FORMATS, PRESETS, COUNCIL_SPECIALISTS, DEFAULT_COUNCIL


def serve(root, config=None, port=8765):
    store=RunStore(root);store.recover_interrupted();config=config or {}
    token=secrets.token_urlsafe(32)
    active={};lock=threading.Lock()
    web=Path(__file__).parent/'web'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,data,content_type='application/json',download=None):
            body=data if isinstance(data,bytes) else json.dumps(data).encode()
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if download:self.send_header('Content-Disposition','attachment; filename="'+download+'"')
            self.end_headers();self.wfile.write(body)
        def same_origin(self):
            return self.headers.get('Host')==f'127.0.0.1:{port}' and self.headers.get('Origin') in (None,f'http://127.0.0.1:{port}')
        def do_GET(self):
            if not self.same_origin():return self.reply(403,{'error':'Loopback origin required'})
            path=urlsplit(self.path).path
            try:
                if path=='/api/config':
                    self.reply(200,{'token':token,'lenses':LENSES,'formats':FORMATS,'presets':PRESETS,
                                    'council_specialists':{key:{'name':v[0],'lens':v[1]} for key,v in COUNCIL_SPECIALISTS.items()},
                                    'default_council':DEFAULT_COUNCIL,
                                    'inspections':[{'id':key,'title':x.get('title',key)} for key,x in config.get('inspections',{}).items()]});return
                if path=='/api/runs':
                    runs=[]
                    for p in sorted(store.root.glob('*/state.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
                        state=json.loads(p.read_text());request=json.loads((p.parent/'brief.json').read_text())
                        runs.append({'id':state['id'],'status':state['status'],'question':request['question'],'parent_id':state.get('parent_id')})
                    self.reply(200,runs);return
                if path.startswith('/api/result/'):
                    run_id=path.rsplit('/',1)[1];directory=store.directory(run_id)
                    report=json.loads((directory/'report.json').read_text())
                    council=directory/'council.json'
                    published=directory/'published-analysis.json'
                    self.reply(200,{'report':report,'council':json.loads(council.read_text()) if council.exists() else None,
                                    'analysis':json.loads(published.read_text()) if published.exists() else None});return
                if path.startswith('/api/runs/'):
                    run_id=path.rsplit('/',1)[1]
                    request=json.loads((store.directory(run_id)/'brief.json').read_text())
                    claims=store.directory(run_id)/'claims.json'
                    withheld=sum(c.get('review') not in ('supported','proposal') for c in json.loads(claims.read_text())) if claims.exists() else None
                    self.reply(200,{**store.read(run_id),'question':request['question'],'lenses':request['lenses'],
                                    'formats':request['formats'],'withheld_claims':withheld});return
                if path.startswith('/outputs/'):
                    _,_,run_id,name=path.split('/')
                    state=store.read(run_id)
                    if name not in state['outputs']:raise FileNotFoundError()
                    file=store.directory(run_id)/'outputs'/name
                    self.reply(200,file.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream',name);return
                files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
                if path not in files:raise FileNotFoundError()
                file=web/files[path]
                self.reply(200,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'text/plain')
            except (ValueError,FileNotFoundError,KeyError):self.reply(404,{'error':'Run or artifact unavailable'})
        def do_POST(self):
            if not self.same_origin() or self.headers.get('X-TMF-Token')!=token:
                return self.reply(403,{'error':'Invalid local workbench request'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=30000:raise ValueError('Request size must be 1–30000 bytes')
                payload=json.loads(self.rfile.read(size))
                if self.path=='/api/brief':return self.reply(200,brief(payload))
                if self.path=='/api/runs':
                    request=brief(payload)
                    if any(x not in config.get('inspections',{}) for x in request['inspections']):raise ValueError('Unknown inspection selection')
                    with lock:
                        if active:return self.reply(409,{'error':'One research job is already active; view or cancel it before starting another'})
                        run_id=store.create(request);engine=ResearchEngine(store,config);active[run_id]=engine
                    def execute():
                        try:engine.execute(run_id)
                        finally:
                            with lock:active.pop(run_id,None)
                    threading.Thread(target=execute,daemon=True).start()
                    return self.reply(202,{'id':run_id})
                if self.path=='/api/refine':
                    parent_id=payload.get('id');feedback=payload.get('feedback')
                    if not isinstance(feedback,str) or not 1<=len(feedback.strip())<=3000:raise ValueError('Provide revision feedback')
                    parent=store.directory(parent_id)
                    if store.read(parent_id)['status'] not in ('completed','partial'):return self.reply(409,{'error':'Wait for the investigation to finish'})
                    if not (parent/'outputs/builder-pack.json').exists():return self.reply(409,{'error':'This run has no retained builder evidence bundle'})
                    with lock:
                        if active:return self.reply(409,{'error':'Wait for the active job before revising'})
                        run_id=store.create(json.loads((parent/'brief.json').read_text()));engine=ResearchEngine(store,config);active[run_id]=engine
                    def revise():
                        try:engine.refine(run_id,parent_id,feedback.strip())
                        finally:
                            with lock:active.pop(run_id,None)
                    threading.Thread(target=revise,daemon=True).start()
                    return self.reply(202,{'id':run_id,'parent_id':parent_id})
                if self.path=='/api/export':
                    run_id=payload.get('id');directory=store.directory(run_id)
                    formats=payload.get('formats',[])
                    if not isinstance(formats,list) or not formats or any(x not in FORMATS for x in formats):raise ValueError('Invalid export selection')
                    with lock:
                        if active:return self.reply(409,{'error':'Wait for the active job before exporting'})
                        prior=store.read(run_id)
                        if prior['status'] not in ('completed','partial'):return self.reply(409,{'error':'No finished research revision is available'})
                        record=json.loads((directory/'report.json').read_text())
                        published=directory/'published-analysis.json'
                        if not published.exists():return self.reply(409,{'error':'This older run has no retained published analysis; do not reuse its rejected draft'})
                        analysis=json.loads(published.read_text())
                        job=SimpleNamespace(cancelled=threading.Event());active[run_id]=job
                        store.update(run_id,status='running',stage='export')
                    def reexport():
                        try:
                            from .exports import export_run
                            def check():
                                if job.cancelled.is_set():raise InterruptedError()
                            revision=uuid.uuid4().hex
                            workspace=directory/'reexports'/revision;workspace.mkdir(parents=True)
                            for name in ('plan.json','claims.json','council.json'):
                                source=directory/name
                                if source.exists():(workspace/name).write_bytes(source.read_bytes())
                            store.event(run_id,'export','Exporting the accepted research revision; no new investigation or model calls.')
                            files,errors=export_run(workspace,record,analysis,list(dict.fromkeys(formats)),config,check)
                            check();dest=directory/'outputs';dest.mkdir(exist_ok=True)
                            names=[]
                            for name in files:
                                new_name='e'+revision[:8]+'-'+name
                                with (dest/new_name).open('xb') as output:output.write((workspace/'outputs'/name).read_bytes())
                                names.append(new_name)
                            with store.lock:
                                check()
                                resolved=[message for message in prior['errors'] if any(message.startswith(f'Requested {fmt} export unavailable')
                                          and not any(e.startswith(f'Requested {fmt} export unavailable') for e in errors) for fmt in formats)]
                                remaining=[message for message in prior['errors'] if message not in resolved]
                                claims_file=directory/'claims.json'
                                research_partial=(any(c.get('review') not in ('supported','proposal') for c in json.loads(claims_file.read_text()))
                                                  if claims_file.exists() else prior['status']=='partial')
                                research_partial=research_partial or any(c.get('status')!='answered' for c in analysis.get('coverage',{}).get('criteria',[]))
                                store.update(run_id,status='partial' if errors or remaining or research_partial else 'completed',stage='done',
                                             outputs=prior['outputs']+names,errors=list(dict.fromkeys(remaining+errors)),
                                             error_history=prior.get('error_history',[])+[{'error':message,'resolved_by_export':revision} for message in resolved])
                        except InterruptedError:store.update(run_id,status='cancelled',stage='cancelled')
                        except Exception as exc:store.update(run_id,status='partial',stage='done',errors=prior['errors']+[f'Additional export failed ({type(exc).__name__}); original artifacts retained'])
                        finally:
                            with lock:active.pop(run_id,None)
                    threading.Thread(target=reexport,daemon=True).start()
                    return self.reply(202,{'id':run_id})
                if self.path=='/api/cancel':
                    with lock:
                        engine=active.get(payload.get('id'))
                        if not engine:return self.reply(409,{'error':'Run is not active'})
                        with store.lock:
                            if store.read(payload['id'])['status'] not in ('queued','running','reviewing','cancelling'):
                                return self.reply(409,{'error':'Run already finished'})
                            engine.cancelled.set();store.update(payload['id'],status='cancelling')
                    return self.reply(202,{'status':'cancelling','note':'In-flight bounded calls finish or time out; no new stages will start.'})
                self.reply(404,{'error':'Unknown action'})
            except (ValueError,TypeError,KeyError,AttributeError):self.reply(400,{'error':'Invalid research brief or request'})
            except OSError:self.reply(404,{'error':'Selected run data is unavailable'})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'TMF Council workbench: http://127.0.0.1:{port}',flush=True)
    prior_signal=None
    if threading.current_thread() is threading.main_thread():
        prior_signal=signal.getsignal(signal.SIGTERM)
        def terminate(signum,frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,terminate)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        with lock:pending=list(active.values())
        for engine in pending:engine.cancelled.set()
        from .processes import cleanup_children
        cleanup_children()
        server.server_close()
        if prior_signal is not None:signal.signal(signal.SIGTERM,prior_signal)
