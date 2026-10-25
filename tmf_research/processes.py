"""Bounded child-process execution for trusted operator-configured adapters."""
import os
import signal
import subprocess
import threading
import time
import atexit
import json
import re

_children=set()
_children_lock=threading.Lock()


def cleanup_children():
    """Reap only child groups created by this adapter module."""
    with _children_lock:children=list(_children)
    for process in children:
        try:
            if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
            elif process.poll() is None:process.kill()
        except ProcessLookupError:pass
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:pass


atexit.register(cleanup_children)


def retained_diagnostic(value, limit=16000):
    """Private partial output, with credential fields/patterns and known environment secrets removed."""
    text = value.decode(errors='replace') if isinstance(value, bytes) else str(value or '')
    secret_name = re.compile(r'token$|secret|password|passwd|api[_-]?key|authorization', re.I)
    known = [v for k, v in os.environ.items() if re.search(r'KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTH', k, re.I) and v]
    def clean_text(text):
        for value in known: text = text.replace(value, '[redacted]')
        text = re.sub(r'(?i)(\bauthorization\s*:\s*)[^\r\n]+', r'\1[redacted]', text)
        text = re.sub(r'(?i)\b(Bearer|Basic)\s+[^\s"\'<>\\]+', r'\1 [redacted]', text)
        text = re.sub(r'(?i)(https?://)[^\s/@]+@', r'\1[redacted]@', text)
        return re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|authorization|token)["\s]*[:=])[^\r\n]*', r'\1[redacted]', text)
    def clean(value):
        if isinstance(value, dict): return {k: '[redacted]' if secret_name.search(k) else clean(v) for k, v in value.items()}
        if isinstance(value, list): return [clean(v) for v in value]
        return clean_text(value) if isinstance(value, str) else value
    lines = []
    for line in text.splitlines():
        try: lines.append(json.dumps(clean(json.loads(line))))
        except ValueError: lines.append(clean_text(line))
    text = '\n'.join(lines)
    return text[:limit] + ('\n[partial diagnostic truncated]' if len(text) > limit else '')


def bounded_run(command, *, input=None, timeout=120, max_output=8_000_000, text=True):
    process=subprocess.Popen(command,stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=os.name=='posix')
    with _children_lock:_children.add(process)
    chunks=[bytearray(),bytearray()];size=0;lock=threading.Lock();overflow=threading.Event()
    def drain(pipe,index):
        nonlocal size
        try:
            while True:
                data=pipe.read(16384)
                if not data:break
                with lock:
                    room=max_output-size
                    chunks[index].extend(data[:max(0,room)]);size+=len(data)
                    if size>max_output:overflow.set();break
        finally:pipe.close()
    def write_input():
        try:process.stdin.write(input.encode() if isinstance(input,str) else input);process.stdin.close()
        except (BrokenPipeError,OSError):pass
    readers=[threading.Thread(target=drain,args=(pipe,i),daemon=True) for i,pipe in enumerate((process.stdout,process.stderr))]
    for thread in readers:thread.start()
    writer=threading.Thread(target=write_input,daemon=True) if input is not None else None
    if writer:writer.start()
    deadline=time.monotonic()+timeout;reason=None
    while process.poll() is None:
        if overflow.is_set():reason='output';break
        if time.monotonic()>=deadline:reason='timeout';break
        try:process.wait(timeout=.05)
        except subprocess.TimeoutExpired:pass
    if reason:
        if os.name=='posix':
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        else:process.kill()
        process.wait(timeout=5)
    elif os.name=='posix':
        # A successful parent must not leave adapter workers or inherited pipes alive.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    for thread in readers:thread.join(timeout=2)
    if writer:writer.join(timeout=2)
    with _children_lock:_children.discard(process)
    if reason=='timeout':raise subprocess.TimeoutExpired(command,timeout,output=bytes(chunks[0]),stderr=bytes(chunks[1]))
    if reason=='output' or overflow.is_set():raise ValueError('Adapter output limit exceeded')
    stdout,stderr=map(bytes,chunks)
    if text:stdout,stderr=stdout.decode(errors='replace'),stderr.decode(errors='replace')
    return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
