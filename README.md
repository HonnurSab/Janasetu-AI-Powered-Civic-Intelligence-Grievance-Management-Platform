# CivicLens ProGIS — PostgreSQL + Role Login + AI + Geospatial Civic Platform

This build implements the complete CivicLens workflow with real citizen registration, separate official department/admin access, PostgreSQL storage, multimedia evidence, Kannada/English complaint input, ML prediction and a professional MapLibre GIS interface.

## What is implemented

### Citizen
- Self-registration using a real email and password.
- Passwords are stored as Werkzeug password hashes, not plain text.
- Citizen login is tied to the registered account.
- Citizen sees only their own private complaints.
- Public city map is privacy-protected and aggregated; it does not expose other citizens' exact locations or identities.
- Report complaints in English or Kannada.
- Attach photos, videos and documents: JPG/JPEG/PNG/WEBP, MP4/MOV/WEBM, PDF/DOC/DOCX.
- Select complaint location by clicking the map, dragging the marker, or using browser GPS.
- ML/category prediction and automatic department routing.

### Department officer
- No public self-registration.
- Credentials are created by the administrator.
- Department login sees only complaints routed to that department.
- Operational GIS map exposes exact complaint locations only for authorized department records.
- Start/resolve complaint workflow, SLA and workload visibility.

### Administrator
- Separate privileged account.
- City/state command-center dashboard.
- Full authorized complaint queue.
- Citizen directory, department performance, officer management and audit logs.
- Create department officer login credentials.
- Professional GIS map with clusters, priority coloring, full-screen controls and heatmap mode.

## GIS architecture

Frontend: MapLibre GL JS + OpenStreetMap tiles.

Database: PostgreSQL. If PostGIS is installed, the app automatically runs `CREATE EXTENSION IF NOT EXISTS postgis`, creates a `geography(Point,4326)` column and a GiST spatial index. If PostGIS is not installed yet, latitude/longitude mapping still works and the application continues running.

For full PostGIS support on Windows, install the PostGIS package for your PostgreSQL version using Stack Builder, then restart PostgreSQL. The next CivicLens startup will initialize the spatial extension automatically if the database user has permission.

## Your local PostgreSQL settings

Your PostgreSQL server is currently using port **2003**.

Create `.env` from the example:

```cmd
copy .env.example .env
notepad .env
```

Set:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:2003/civiclens
SECRET_KEY=replace-with-a-long-random-random-secret
FLASK_DEBUG=1
SEED_DEMO_DATA=true
PORT=5000
SESSION_COOKIE_SECURE=false
MAX_UPLOAD_MB=180
```

Do not share or commit the real `.env` file.

If your PostgreSQL password contains characters such as `@`, `:`, `/`, `?`, `#` or `%`, URL-encode the password in `DATABASE_URL`.

## Install and run

From the project folder:

```cmd
python -m pip install -r requirements.txt
python -m flask --app app init-db
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Health check:

```text
http://127.0.0.1:5000/health
```

A healthy response reports PostgreSQL, model status and whether PostGIS is enabled.

## Demo credentials

Citizen:

```text
citizen1@civiclens.local
Citizen@123
```

Roads department:

```text
roads_and_infrastructure@civiclens.local
Dept@123
```

Administrator:

```text
admin@civiclens.local
Admin@123
```

Real citizens are not limited to these demo accounts. They use **Create a citizen account** on the login page and register with their own email/password.

## ML model

The supplied TF-IDF vectorizer and Logistic Regression model are used for English complaint prediction. The project pins `scikit-learn==1.6.1` to match the model serialization version.

Kannada text is detected using the Kannada Unicode range and routed through a Kannada civic keyword classifier for the included categories. The original Kannada text remains stored in PostgreSQL.

For a future production-grade multilingual model, replace the Kannada keyword layer with a trained multilingual classifier while keeping the current API contract.

## File storage

Uploaded evidence is stored locally under:

```text
uploads/<complaint_id>/
```

PostgreSQL stores only attachment metadata and the protected file reference. Access to evidence is checked by role before the file is returned.

For production deployment, replace local uploads with object storage such as S3-compatible storage and keep the metadata in PostgreSQL.

## Privacy boundaries

Citizen: public aggregated statistics/maps + only their own complaint records and attachments.

Department: only complaints and evidence assigned to their department.

Administrator: authorized city/state operational data.

All important account/complaint actions are recorded in `audit_logs`.

## Production deployment notes

Before public deployment:
- set `FLASK_DEBUG=0`;
- set `SEED_DEMO_DATA=false`;
- use a strong random `SECRET_KEY`;
- deploy behind HTTPS and set `SESSION_COOKIE_SECURE=true`;
- use managed PostgreSQL/PostGIS and backups;
- use production object storage for media;
- add verified-email delivery, password reset and rate limiting;
- review retention/privacy requirements for citizen PII and evidence.

## Janasetu UI upgrade (2026-09)

This build preserves the existing Flask/PostgreSQL/ML/local-AI architecture and adds:

- Premium Janasetu branding with the supplied logo.
- Animated KPI cards, micro-interactions and responsive command-centre styling.
- Karnataka district boundary layer with clickable district intelligence.
- Taluk/sub-district boundary mode using a browser-loaded administrative GeoJSON layer.
- Karnataka state view, district filtering, clusters, heatmap and multiple basemaps.
- Complaint markers that open the complete case drawer.
- Real evidence listing/preview links with role-based authorization.
- Complaint timeline backed by `complaint_updates`.
- Department resolution workflow with resolution text, action, officer remarks and resolution evidence.
- Citizen-visible resolution tab, closing the Report → Route → Resolve loop.
- One-page citizen issue reporting with AI classification, priority, location and attachments.
- All demo department credentials visible in the demo-login disclosure.

The GIS boundary layer is loaded from public geospatial datasets at runtime. For production deployment, pin and redistribute the required GeoJSON assets under `static/geo/` after validating the licensing and update cadence appropriate for the deployment.


## Local AI responsiveness
The Janasetu AI endpoint disables Qwen3 thinking mode for short civic responses, keeps the model warm for 10 minutes, limits output to 160 tokens, and answers common department-routing questions instantly. If Ollama is not running, the UI reports that separately.

## Evidence Intelligence upgrade

Citizen evidence is validated on both the browser and server.

- Up to **5 images**, maximum **10 MB each**.
- Up to **1 video**, maximum **60 seconds** and **100 MB**.
- Documents are limited to **20 MB each**.
- Maximum **6 evidence files** on a complaint.
- Images can contribute EXIF GPS/capture metadata when available.
- If a citizen submits media without text, they select the civic category manually; this avoids pretending a text-only classifier can understand an image/video.
- Media-only complaints require a map/GPS location unless a submitted image contains usable EXIF GPS.
- Video duration/resolution are validated with OpenCV and a secure video thumbnail is generated for the complaint drawer.
- Original images/videos remain protected by the existing role-based evidence endpoint.
- Resolution proof uses the same validation pipeline.

No new trained computer-vision model is required for this workflow. The existing ML classifier continues to classify complaint text; media is treated as evidence with metadata/location validation.

## Fast local AI (no RAG)

For much faster local responses, install the small Qwen model once:

```cmd
setup_fast_ai.bat
```

or:

```cmd
ollama pull qwen3:0.6b
```

Janasetu prefers models in this order when installed: `qwen3:0.6b`, `gemma3:1b`, `llama3.2:1b`, `qwen3:1.7b`, then `qwen3:4b`.

Common department/evidence/status questions use the instant Janasetu civic engine and do not wait for an LLM. For other questions, the selected local model uses thinking disabled, a small context, a short answer limit, and a 25-second server cap. If Ollama is slow or unavailable, the API returns a safe Janasetu fallback rather than a timeout error.

## OTP and deployment update

This build includes a production-ready OTP integration layer with 2Factor SMS support, SMTP email OTP, rate/expiry/attempt controls, development OTP mode, and an optional **Register without OTP** path controlled by `ALLOW_UNVERIFIED_REGISTRATION`.

For deployment, use `FLASK_DEBUG=0`, a strong `SECRET_KEY`, `SESSION_COOKIE_SECURE=true` behind HTTPS, a managed PostgreSQL database, and real OTP/SMTP credentials. See `DEPLOYMENT.md`.
