@echo off
cd /d C:\Users\briza\viaeduca_api
call .venv\Scripts\activate.bat
python -m crud.sync >> logs\sync_capes.log 2>&1