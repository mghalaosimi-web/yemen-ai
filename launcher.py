"""Yemen AI Desktop Launcher: starts the local server and opens the UI."""
from __future__ import annotations
import atexit, os, socket, subprocess, sys, time, webbrowser
from pathlib import Path

HOST='127.0.0.1'; PORT=int(os.getenv('YEMEN_AI_PORT','8765'))
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
LOCK=Path(os.getenv('TEMP',str(ROOT)))/'YemenAI.lock'
proc=None

def port_open():
    try:
        with socket.create_connection((HOST,PORT),timeout=.5): return True
    except OSError: return False

def cleanup():
    global proc
    if proc and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()
    try: LOCK.unlink(missing_ok=True)
    except Exception: pass

def ensure_runtime():
    try:
        import fastapi, uvicorn, multipart
        return True
    except Exception:
        req=ROOT/'requirements.txt'
        if not req.exists(): raise SystemExit('Missing requirements.txt')
        print('Preparing Yemen AI runtime dependencies...')
        r=subprocess.run([sys.executable,'-m','pip','install','-r',str(req)],cwd=ROOT)
        if r.returncode!=0: raise SystemExit('Dependency installation failed. Run: py -m pip install -r requirements.txt')

def main():
    global proc
    ensure_runtime()
    if LOCK.exists() and port_open():
        webbrowser.open(f'http://{HOST}:{PORT}/'); return
    LOCK.write_text(str(os.getpid()),encoding='utf-8'); atexit.register(cleanup)
    cmd=[sys.executable,'-m','uvicorn','main:app','--host',HOST,'--port',str(PORT)]
    proc=subprocess.Popen(cmd,cwd=ROOT)
    deadline=time.time()+25
    while time.time()<deadline:
        if port_open():
            webbrowser.open(f'http://{HOST}:{PORT}/'); break
        if proc.poll() is not None: raise SystemExit('Yemen AI server failed to start. Check the error above; dependencies are installed automatically by this launcher.')
        time.sleep(.25)
    else: raise SystemExit('Yemen AI startup timeout')
    try:
        while proc.poll() is None: time.sleep(1)
    except KeyboardInterrupt: pass

if __name__=='__main__': main()
