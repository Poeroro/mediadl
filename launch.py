import subprocess, sys, os

os.chdir("/home/ubuntu/mediadl")
p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8181"],
    stdout=open("/tmp/mediadl.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print(f"PID={p.pid}")
