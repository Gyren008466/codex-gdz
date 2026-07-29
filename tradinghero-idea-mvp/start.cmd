@echo off
setlocal
set "NODE_EXE=C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
set "APP_DIR=%~dp0"
"%NODE_EXE%" "%APP_DIR%server.js"
