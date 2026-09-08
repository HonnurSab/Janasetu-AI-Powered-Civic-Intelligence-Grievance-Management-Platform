@echo off
if not exist .env copy .env.example .env
echo Edit .env and set your PostgreSQL password first.
python -m pip install -r requirements.txt
python -m flask --app app init-db
python app.py
pause
