@echo off
title AI Builder Starter

echo.
echo =================================================
echo      Starting AI Builder SPA Environment
echo =================================================
echo.

echo [1/3] Starting backend server (FastAPI)...
:: Inicia o backend em uma nova janela com o título "Backend Server"
start "Backend Server" cmd /k "echo Starting backend... && PYTHONPATH=src poetry run python -m server.pdf_training_app.main"

echo [2/3] Starting frontend server (React)...
:: Inicia o frontend em uma nova janela com o título "Frontend Server"
start "Frontend Server" cmd /k "echo Starting frontend... && cd src/spa && npm run dev"

echo.
echo Waiting for servers to initialize (approx. 8 seconds)...
timeout /t 15 /nobreak > nul

echo [3/3] Opening application in your default browser...
start http://localhost:5173

echo.
echo =================================================
echo      SUCCESS!
echo =================================================
echo.
echo - Your application is running.
echo - To stop the application, simply close the two new command prompt windows.
echo.