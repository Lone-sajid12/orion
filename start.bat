@echo off
REM ORION launcher for Windows. Double-click or run: start.bat
cd /d "%~dp0"
where python >nul 2>nul || (echo ORION needs Python installed. See README. & pause & exit /b 1)
where npm >nul 2>nul || (echo ORION needs Node.js installed. See README. & pause & exit /b 1)
if not exist backend\.deps-ok (
  echo Installing Python dependencies (one-time)...
  python -m pip install -r backend\requirements.txt
  type nul > backend\.deps-ok
)
if not exist frontend\node_modules (
  echo Installing frontend dependencies (one-time)...
  pushd frontend && npm install && popd
)
echo Starting ORION engine     -^> http://localhost:8000
echo Starting ORION interface  -^> http://localhost:5173
start "ORION engine" cmd /k "cd backend && python -m uvicorn app:app --host 127.0.0.1 --port 8000"
start "ORION interface" cmd /k "cd frontend && npm run dev"
echo ORION is starting in two windows. Open http://localhost:5173 in your browser.
pause
