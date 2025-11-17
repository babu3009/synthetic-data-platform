@echo off
cd /d C:\Code\python\synthetic-data-platform\apps\backend
C:\pyenv\.conda\envs\conda-synthetic-data\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
