@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the local environment first:
  echo python -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo Opening Condorcet at http://127.0.0.1:8501
start "" "http://127.0.0.1:8501"
".venv\Scripts\python.exe" -m streamlit run ui/app.py --server.port 8501 --server.address 127.0.0.1 --browser.gatherUsageStats false
