@echo off
setlocal
py run_closed_loop_demo.py --output runs\closed-loop
if errorlevel 1 exit /b %errorlevel%
start "CogniGuide round 2 report" "runs\closed-loop\round-2\report.html"
