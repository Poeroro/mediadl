import subprocess, sys, os
from pathlib import Path

os.chdir(Path(__file__).parent)
p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8181"],
    stdout=open(Path(__file__).parent / "mediadl.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print(f"PID={p.pid}")
