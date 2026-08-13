@echo off
setlocal
cd /d "%~dp0"

if "%COGNIGUIDE_TOOL_PORT%"=="" set "COGNIGUIDE_TOOL_PORT=18089"
py tools\mock_tool_server.py --host 0.0.0.0 --port %COGNIGUIDE_TOOL_PORT%
