@echo off
setlocal
py run_demo.py --input examples\python_foundations.json --output runs\python-foundations
if errorlevel 1 exit /b %errorlevel%
start "CogniGuide report" "runs\python-foundations\report.html"
