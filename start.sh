#!/bin/bash
cd /home/ubuntu/mediadl
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 8181 2>&1
