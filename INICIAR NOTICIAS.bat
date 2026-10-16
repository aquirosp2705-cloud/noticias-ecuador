@echo off
title Noticias Ecuador - no cierres esta ventana mientras uses el programa
cd /d "%~dp0"
set "PY=C:\Program Files\Python312\python.exe"
if not exist "%PY%" set "PY=python"
echo.
echo   Noticias Ecuador se esta abriendo en tu navegador...
echo   Mientras lo uses, deja esta ventana abierta (puedes minimizarla).
echo   Para cerrarla, cierra esta ventana o presiona Ctrl+C.
echo.
"%PY%" server.py
if errorlevel 1 (
  echo.
  echo   El programa se detuvo con un error. Toma una foto de esta ventana.
  pause
)
