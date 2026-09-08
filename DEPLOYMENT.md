# Janasetu deployment

## Production environment variables

Set these in your hosting platform rather than committing real secrets:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/civiclens
SECRET_KEY=<long-random-secret>
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=true
ALLOW_UNVERIFIED_REGISTRATION=false
DEV_OTP=false

OLLAMA_BASE_URL=http://ollama:11434
AI_FAST_MODEL=qwen3:0.6b
AI_TIMEOUT_SECONDS=15

OTP_PROVIDER=2factor
OTP_API_MODE=v4
OTP_API_URL=https://2factor.in/API/V1/OTP/SEND
OTP_API_KEY=<2factor-api-key>
OTP_TEMPLATE_NAME=LOGIN_OTP
OTP_TTL_SECONDS=300
OTP_MAX_ATTEMPTS=5

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<sender-email>
SMTP_PASSWORD=<smtp-app-password>
SMTP_FROM=<sender-email>
```

## OTP

Janasetu keeps OTP verification in the backend. The SMS API key is never sent to the browser. The 2Factor integration uses its REST OTP endpoint and sends the locally generated six-digit code as `var1`. Configure the matching SMS template in the provider account.

If you are only demonstrating locally, set `DEV_OTP=true`. No external SMS or email provider is contacted; the OTP is printed to the Flask terminal and returned only in the development response.

## Optional registration bypass

For a public deployment, keep:

```env
ALLOW_UNVERIFIED_REGISTRATION=false
```

For a controlled demo where you explicitly want the second registration path, set it to `true`. The registration page then shows **Register without OTP** alongside **Create account & verify**.

## Docker

```bash
docker compose up --build
```

For production, replace all placeholder secrets and use a managed PostgreSQL database. Do not expose PostgreSQL publicly.

## Local Windows run

```cmd
python -m pip install -r requirements.txt
python -m flask --app app init-db
python app.py
```

For production-style local serving:

```cmd
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Windows deployments should use a Linux host/container for Gunicorn.
