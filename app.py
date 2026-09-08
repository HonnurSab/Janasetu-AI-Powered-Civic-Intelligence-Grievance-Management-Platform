from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, abort
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os, re, uuid, mimetypes, joblib, pandas as pd, numpy as np, requests, json, math, shutil, secrets, smtplib, ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

try:
    from PIL import Image, ExifTags
except Exception:
    Image = None
    ExifTags = None

try:
    import cv2
except Exception:
    cv2 = None

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/civiclens')
CSV = BASE / 'model' / 'smart_city_complaints_10000_rich_text.csv'
MODEL = BASE / 'model' / 'logreg_model.pkl'
VEC = BASE / 'model' / 'tfidf_vectorizer.pkl'
UPLOAD_ROOT = BASE / 'uploads'
UPLOAD_ROOT.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'CHANGE-ME-IN-PRODUCTION')
app.config.update(JSON_SORT_KEYS=False, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE','false').lower()=='true',
                  MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_MB','180'))*1024*1024)
pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=10, open=False, kwargs={'row_factory': dict_row})

DEPT = {
    'Garbage & Sanitation':'Solid Waste Management', 'Roads & Footpaths':'Roads & Infrastructure',
    'Water Supply':'Water Supply & Sewerage', 'Streetlights & Electricity':'Electricity Utility',
    'Drainage & Flooding':'Storm Water Drainage', 'Public Safety':'Police & Public Safety', 'Other':'Ward Office'
}
CATEGORIES=list(DEPT); DEPARTMENTS=list(DEPT.values()); PRIORITIES=['Critical','High','Medium','Low']
STATUSES=['New','Assigned','In Progress','Awaiting Verification','Resolved','Rejected']
WARDS=['Whitefield','Mahadevapura','KR Puram','Marathahalli','Bellandur']
DISTRICTS=['Bagalkot','Ballari','Belagavi','Bengaluru Rural','Bengaluru Urban','Bidar','Chamarajanagar','Chikkaballapura','Chikkamagaluru','Chitradurga','Dakshina Kannada','Davanagere','Dharwad','Gadag','Hassan','Haveri','Kalaburagi','Kodagu','Kolar','Koppal','Mandya','Mysuru','Raichur','Ramanagara','Shivamogga','Tumakuru','Udupi','Uttara Kannada','Vijayanagara','Vijayapura','Yadgir']
ALLOWED_EXT={'jpg','jpeg','png','webp','mp4','mov','webm','pdf','doc','docx'}
IMAGE_EXT={'jpg','jpeg','png','webp'}
VIDEO_EXT={'mp4','mov','webm'}
DOCUMENT_EXT={'pdf','doc','docx'}
MAX_IMAGE_BYTES=int(os.getenv('MAX_IMAGE_MB','10'))*1024*1024
MAX_VIDEO_BYTES=int(os.getenv('MAX_VIDEO_MB','100'))*1024*1024
MAX_DOCUMENT_BYTES=int(os.getenv('MAX_DOCUMENT_MB','20'))*1024*1024
MAX_VIDEO_SECONDS=int(os.getenv('MAX_VIDEO_SECONDS','60'))
MAX_IMAGES_PER_COMPLAINT=int(os.getenv('MAX_IMAGES_PER_COMPLAINT','5'))
MAX_VIDEOS_PER_COMPLAINT=int(os.getenv('MAX_VIDEOS_PER_COMPLAINT','1'))
MAX_FILES_PER_COMPLAINT=int(os.getenv('MAX_FILES_PER_COMPLAINT','6'))
OTP_LENGTH=6
OTP_MAX_ATTEMPTS=int(os.getenv('OTP_MAX_ATTEMPTS','5'))
OTP_PROVIDER=os.getenv('OTP_PROVIDER','2factor').lower()
OTP_API_KEY=os.getenv('OTP_API_KEY','')
OTP_API_URL=os.getenv('OTP_API_URL','https://2factor.in/API/V1/OTP/SEND')
OTP_API_MODE=os.getenv('OTP_API_MODE','v4').lower()
OTP_TEMPLATE_NAME=os.getenv('OTP_TEMPLATE_NAME','LOGIN_OTP')
OTP_COUNTRY_CODE=os.getenv('OTP_COUNTRY_CODE','91')
OTP_TTL_SECONDS=int(os.getenv('OTP_TTL_SECONDS','300'))
SMTP_HOST=os.getenv('SMTP_HOST','')
SMTP_PORT=int(os.getenv('SMTP_PORT','587'))
SMTP_USERNAME=os.getenv('SMTP_USERNAME','')
SMTP_PASSWORD=os.getenv('SMTP_PASSWORD','')
SMTP_FROM=os.getenv('SMTP_FROM',SMTP_USERNAME)
DEV_OTP=os.getenv('DEV_OTP','false').lower()=='true'
ALLOW_UNVERIFIED_REGISTRATION=os.getenv('ALLOW_UNVERIFIED_REGISTRATION','true').lower()=='true'
KANNADA_RE=re.compile(r'[\u0C80-\u0CFF]')
KANNADA_KEYWORDS={
    'Roads & Footpaths':['ಗುಂಡಿ','ರಸ್ತೆ','ಫುಟ್ಪಾತ್','ಪಾದಚಾರಿ','ರಸ್ತೆಯ'],
    'Garbage & Sanitation':['ಕಸ','ತ್ಯಾಜ್ಯ','ಸ್ವಚ್ಛತೆ','ಕಸದ'],
    'Water Supply':['ನೀರು','ನೀರಿನ','ಕುಡಿಯುವ'],
    'Drainage & Flooding':['ಚರಂಡಿ','ಒಳಚರಂಡಿ','ನೆರೆ','ಪ್ರವಾಹ','ನಿಂತ ನೀರು'],
    'Streetlights & Electricity':['ಬೀದಿ ದೀಪ','ವಿದ್ಯುತ್','ಲೈಟ್','ದೀಪ'],
    'Public Safety':['ಅಪಾಯ','ಪೊಲೀಸ್','ಸುರಕ್ಷತೆ','ಅಪಘಾತ']
}

try:
    model=joblib.load(MODEL); vectorizer=joblib.load(VEC)
except Exception as e:
    print('Model load warning:',e); model=vectorizer=None


def utcnow(): return datetime.now(timezone.utc)
def get_conn():
    if pool.closed: pool.open(wait=True)
    return pool.connection()
def one(sql,args=()):
    with get_conn() as conn, conn.cursor() as cur: cur.execute(sql,args); return cur.fetchone()
def rows(sql,args=()):
    with get_conn() as conn, conn.cursor() as cur: cur.execute(sql,args); return cur.fetchall()
def execute(sql,args=()):
    with get_conn() as conn, conn.cursor() as cur: cur.execute(sql,args); conn.commit()
def current_user(): return session.get('user')

def login_required(fn):
    @wraps(fn)
    def w(*a,**k):
        if not current_user():
            return jsonify(error='Authentication required'),401 if request.path.startswith('/api/') else redirect(url_for('login'))
        return fn(*a,**k)
    return w

def roles_required(*allowed):
    def deco(fn):
        @wraps(fn)
        def w(*a,**k):
            u=current_user()
            if not u: return jsonify(error='Authentication required'),401
            if u['role'] not in allowed: return jsonify(error='Forbidden'),403
            return fn(*a,**k)
        return w
    return deco

def migrate_existing(cur):
    # Makes old databases compatible without requiring users to drop data.
    for stmt in [
        "ALTER TABLE citizens ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE citizens ADD COLUMN IF NOT EXISTS district VARCHAR(120)",
        "ALTER TABLE citizens ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(10) DEFAULT 'en'",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS district VARCHAR(120)",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE officers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE",
        "UPDATE users SET email=user_id WHERE email IS NULL",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS original_language VARCHAR(10) DEFAULT 'en'",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS translated_text TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS district VARCHAR(120)",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS sla_deadline TIMESTAMPTZ",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS ai_category_confidence DOUBLE PRECISION",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS location_source VARCHAR(30) DEFAULT 'manual'",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS original_name TEXT",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS mime_type VARCHAR(160)",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS file_size BIGINT",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS media_type VARCHAR(30)",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) DEFAULT 'complaint'",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS captured_at TIMESTAMPTZ",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS duration_seconds DOUBLE PRECISION",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS width INTEGER",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS height INTEGER",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS validation_status VARCHAR(40) DEFAULT 'accepted'",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS metadata_json TEXT",
        "ALTER TABLE evidence ADD COLUMN IF NOT EXISTS thumbnail_url TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS resolution_text TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS resolution_action TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS resolution_remarks TEXT",
        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS resolution_by VARCHAR(120)"
    ]:
        try: cur.execute(stmt)
        except Exception: pass

def init_postgis(cur):
    enabled=False
    try:
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        cur.execute("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS location geography(Point,4326)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_complaints_location_gist ON complaints USING GIST(location)")
        enabled=True
    except Exception as e:
        print('PostGIS optional feature unavailable:',e)
    return enabled

def init_db(seed=True):
    schema=(BASE/'schema.sql').read_text(encoding='utf-8')
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(schema); migrate_existing(cur)
        cur.execute("""CREATE TABLE IF NOT EXISTS otp_verifications (
            id BIGSERIAL PRIMARY KEY,
            channel VARCHAR(20) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            otp_hash VARCHAR(255) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            verified BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_otp_destination ON otp_verifications(channel,destination,created_at DESC)")
        for stmt in [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_complaints_geo ON complaints(latitude, longitude)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_complaint ON evidence(complaint_id)"
        ]:
            try: cur.execute(stmt)
            except Exception: pass
        for category,department in DEPT.items():
            cur.execute("INSERT INTO departments(name,category,district) VALUES (%s,%s,%s) ON CONFLICT (name) DO UPDATE SET category=EXCLUDED.category",
                        (department,category,'Bengaluru Urban'))
        conn.commit()
        try:
            init_postgis(cur); conn.commit()
        except Exception: conn.rollback()
    if not seed: return
    with get_conn() as conn, conn.cursor() as cur:
        names=['Ananya Rao','Arjun Kumar','Meera Nair','Rohan Shetty','Kavya Iyer','Vikram Singh']
        for i in range(1,11):
            cid=f'CIT-{i:04d}'; email=f'citizen{i}@civiclens.local'
            cur.execute("""INSERT INTO citizens(citizen_id,name,email,phone,address,district,ward,preferred_language)
                         VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (citizen_id) DO NOTHING""",
                        (cid,names[(i-1)%len(names)],email,f'+91-90000-{i:05d}','Demo address','Bengaluru Urban',WARDS[(i-1)%len(WARDS)],'en'))
            cur.execute("""INSERT INTO users(user_id,email,role,password_hash,citizen_id)
                         VALUES (%s,%s,'citizen',%s,%s) ON CONFLICT (user_id) DO NOTHING""",
                        (email,email,generate_password_hash('Citizen@123'),cid))
        for dep in DEPARTMENTS:
            cur.execute('SELECT department_id FROM departments WHERE name=%s',(dep,)); did=cur.fetchone()['department_id']
            em=dep.lower().replace(' ','_').replace('&','and')+'@civiclens.local'
            cur.execute("""INSERT INTO officers(name,email,department_id) VALUES (%s,%s,%s)
                         ON CONFLICT (email) DO UPDATE SET department_id=EXCLUDED.department_id RETURNING officer_id""",
                        (dep+' Officer',em,did)); oid=cur.fetchone()['officer_id']
            cur.execute("""INSERT INTO users(user_id,email,role,password_hash,officer_id)
                         VALUES (%s,%s,'department',%s,%s) ON CONFLICT (user_id) DO NOTHING""",
                        (em,em,generate_password_hash('Dept@123'),oid))
        cur.execute("""INSERT INTO users(user_id,email,role,password_hash)
                     VALUES (%s,%s,'admin',%s) ON CONFLICT (user_id) DO NOTHING""",
                    ('admin@civiclens.local','admin@civiclens.local',generate_password_hash('Admin@123')))
        conn.commit()
    # Small demo sample with Bengaluru coordinates; real citizen records remain separate.
    if one('SELECT COUNT(*) n FROM complaints')['n']==0:
        sample=[
            ('Large pothole near bus stop','Roads & Footpaths',12.9719,77.5948,'Whitefield'),
            ('Garbage has not been collected','Garbage & Sanitation',12.9781,77.6032,'Mahadevapura'),
            ('Water pipe leakage on main road','Water Supply',12.9607,77.6010,'KR Puram'),
            ('Streetlight not working','Streetlights & Electricity',12.9672,77.5874,'Marathahalli'),
            ('Drainage overflowing after rain','Drainage & Flooding',12.9561,77.6121,'Bellandur')]
        for i,(text,cat,lat,lng,ward) in enumerate(sample,1):
            did=one('SELECT department_id FROM departments WHERE name=%s',(DEPT[cat],))['department_id']
            cid=f'DEMO-{i:04d}'
            execute("""INSERT INTO complaints(complaint_id,citizen_id,complaint_text,category,priority,status,department_id,district,ward,latitude,longitude,sla_hours,sla_deadline,ai_category_confidence)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (cid,f'CIT-{i:04d}',text,cat,'High' if i in (1,5) else 'Medium','New',did,'Bengaluru Urban',ward,lat,lng,48,utcnow()+timedelta(hours=48),.92))
            sync_postgis(cid,lat,lng)

def sync_postgis(cid,lat,lng):
    try:
        execute("UPDATE complaints SET location=ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography WHERE complaint_id=%s",(lng,lat,cid))
    except Exception: pass

def log(role,uid,action,cid=None):
    try: execute('INSERT INTO audit_logs(user_role,user_id,action,complaint_id) VALUES (%s,%s,%s,%s)',(role,uid,action,cid))
    except Exception: pass

def detect_language(text): return 'kn' if KANNADA_RE.search(text or '') else 'en'
def predict(text):
    lang=detect_language(text)
    if lang=='kn':
        for cat,words in KANNADA_KEYWORDS.items():
            if any(w in text for w in words): return cat,.90,lang
        return 'Other',.55,lang
    if model is not None and vectorizer is not None:
        p=model.predict_proba(vectorizer.transform([text]))[0]; i=int(np.argmax(p)); return str(model.classes_[i]),float(p[i]),lang
    return 'Other',.35,lang

def _gps_decimal(values, ref):
    try:
        deg, minutes, seconds = [float(x) for x in values]
        out = deg + minutes/60.0 + seconds/3600.0
        if str(ref).upper() in ('S','W'): out = -out
        return out
    except Exception:
        return None

def image_metadata(path: Path):
    meta={'width':None,'height':None,'latitude':None,'longitude':None,'captured_at':None,'validation_status':'accepted'}
    if Image is None:
        meta['validation_status']='accepted_no_image_metadata'; return meta
    try:
        with Image.open(path) as im:
            meta['width'],meta['height']=im.size
            exif=im.getexif()
            if not exif: return meta
            decoded={}
            for key,val in exif.items():
                decoded[ExifTags.TAGS.get(key,key) if ExifTags else key]=val
            dt=decoded.get('DateTimeOriginal') or decoded.get('DateTime')
            if dt:
                try: meta['captured_at']=datetime.strptime(str(dt),'%Y:%m:%d %H:%M:%S').replace(tzinfo=timezone.utc)
                except Exception: pass
            gps_raw=None
            try:
                gps_raw=exif.get_ifd(34853) if hasattr(exif,'get_ifd') else decoded.get('GPSInfo')
            except Exception:
                gps_raw=decoded.get('GPSInfo')
            if gps_raw and ExifTags:
                gps={ExifTags.GPSTAGS.get(k,k):v for k,v in gps_raw.items()}
                lat=_gps_decimal(gps.get('GPSLatitude',[]),gps.get('GPSLatitudeRef','N'))
                lng=_gps_decimal(gps.get('GPSLongitude',[]),gps.get('GPSLongitudeRef','E'))
                if lat is not None and lng is not None and -90<=lat<=90 and -180<=lng<=180:
                    meta['latitude'],meta['longitude']=lat,lng
    except Exception as exc:
        meta['validation_status']='accepted_metadata_unavailable'; meta['metadata_error']=str(exc)[:180]
    return meta

def video_metadata(path: Path, create_thumbnail=True):
    meta={'width':None,'height':None,'duration_seconds':None,'validation_status':'accepted','thumbnail_path':None}
    if cv2 is None:
        meta['validation_status']='accepted_duration_unverified'; return meta
    cap=None
    try:
        cap=cv2.VideoCapture(str(path))
        if not cap.isOpened():
            meta['validation_status']='accepted_duration_unverified'; return meta
        fps=float(cap.get(cv2.CAP_PROP_FPS) or 0); frames=float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        meta['width']=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        meta['height']=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        if fps>0 and frames>=0: meta['duration_seconds']=frames/fps
        if create_thumbnail and frames>0:
            cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,int(frames*0.25))); ok,frame=cap.read()
            if ok:
                thumb_dir=path.parent/'thumbs'; thumb_dir.mkdir(exist_ok=True)
                thumb=thumb_dir/(path.stem+'_thumb.jpg'); cv2.imwrite(str(thumb),frame); meta['thumbnail_path']=thumb
    except Exception as exc:
        meta['validation_status']='accepted_duration_unverified'; meta['metadata_error']=str(exc)[:180]
    finally:
        try:
            if cap is not None: cap.release()
        except Exception: pass
    return meta

def validate_and_save_evidence(file_storage,cid,uploader,purpose='complaint'):
    if not file_storage or not file_storage.filename: return None,'Empty attachment.'
    ext=file_storage.filename.rsplit('.',1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ALLOWED_EXT: return None,f'Unsupported file type: {file_storage.filename}'
    stream=file_storage.stream; pos=stream.tell(); stream.seek(0,2); size=stream.tell(); stream.seek(pos)
    if ext in IMAGE_EXT and size>MAX_IMAGE_BYTES: return None,f'Image {file_storage.filename} exceeds {MAX_IMAGE_BYTES//1024//1024} MB.'
    if ext in VIDEO_EXT and size>MAX_VIDEO_BYTES: return None,f'Video {file_storage.filename} exceeds {MAX_VIDEO_BYTES//1024//1024} MB.'
    if ext in DOCUMENT_EXT and size>MAX_DOCUMENT_BYTES: return None,f'Document {file_storage.filename} exceeds {MAX_DOCUMENT_BYTES//1024//1024} MB.'
    folder=UPLOAD_ROOT/cid; folder.mkdir(parents=True,exist_ok=True)
    safe=secure_filename(file_storage.filename) or ('evidence.'+ext); unique=f"{uuid.uuid4().hex[:12]}_{safe}"; path=folder/unique; file_storage.save(path)
    mime=file_storage.mimetype or mimetypes.guess_type(safe)[0] or 'application/octet-stream'
    media='image' if ext in IMAGE_EXT or mime.startswith('image/') else 'video' if ext in VIDEO_EXT or mime.startswith('video/') else 'document'
    meta={'width':None,'height':None,'latitude':None,'longitude':None,'captured_at':None,'duration_seconds':None,'validation_status':'accepted','thumbnail_path':None}
    if media=='image': meta.update(image_metadata(path))
    elif media=='video':
        meta.update(video_metadata(path))
        if meta.get('duration_seconds') is not None and meta['duration_seconds']>MAX_VIDEO_SECONDS+0.75:
            try:
                if meta.get('thumbnail_path'): Path(meta['thumbnail_path']).unlink(missing_ok=True)
                path.unlink(missing_ok=True)
            except Exception: pass
            return None,f'Video {file_storage.filename} is {meta["duration_seconds"]:.1f}s. Maximum allowed duration is {MAX_VIDEO_SECONDS}s.'
    thumb_rel=str(Path(meta['thumbnail_path']).relative_to(BASE)) if meta.get('thumbnail_path') else None
    metadata_for_db={k:v for k,v in meta.items() if k not in ('captured_at','thumbnail_path')}
    execute("""INSERT INTO evidence(complaint_id,file_url,original_name,mime_type,file_size,media_type,purpose,uploaded_by,latitude,longitude,captured_at,duration_seconds,width,height,validation_status,metadata_json,thumbnail_url)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (cid,str(path.relative_to(BASE)),file_storage.filename,mime,path.stat().st_size,media,purpose,uploader,meta.get('latitude'),meta.get('longitude'),meta.get('captured_at'),meta.get('duration_seconds'),meta.get('width'),meta.get('height'),meta.get('validation_status','accepted'),json.dumps(metadata_for_db,default=str,ensure_ascii=False),thumb_rel))
    return {'name':file_storage.filename,'type':media,'size':path.stat().st_size,'latitude':meta.get('latitude'),'longitude':meta.get('longitude'),'duration_seconds':meta.get('duration_seconds'),'validation_status':meta.get('validation_status')},None

def validate_file_counts(files):
    valid=[f for f in files if f and f.filename]
    if len(valid)>MAX_FILES_PER_COMPLAINT: return f'Maximum {MAX_FILES_PER_COMPLAINT} evidence files per complaint.'
    images=sum(1 for f in valid if f.filename.rsplit('.',1)[-1].lower() in IMAGE_EXT)
    videos=sum(1 for f in valid if f.filename.rsplit('.',1)[-1].lower() in VIDEO_EXT)
    if images>MAX_IMAGES_PER_COMPLAINT: return f'Maximum {MAX_IMAGES_PER_COMPLAINT} images per complaint.'
    if videos>MAX_VIDEOS_PER_COMPLAINT: return f'Maximum {MAX_VIDEOS_PER_COMPLAINT} video per complaint.'
    return None

def _fallback_ai_answer(question):
    q=(question or '').lower()
    mapping=[
      (('pothole','potholes','path hole','road damage','footpath','ಗುಂಡಿ','ರಸ್ತೆ'),'Pothole, damaged-road and footpath complaints are handled by Roads & Infrastructure. Use Report Issue to add the location and photo/video evidence.'),
      (('garbage','waste','dumping','litter','ಕಸ','ತ್ಯಾಜ್ಯ'),'Garbage, waste-dumping and sanitation complaints are handled by Solid Waste Management. Add a location and photo/video when available.'),
      (('water leakage','water leak','no water','water supply','ನೀರು','ಸೋರಿಕೆ'),'Water-supply and leakage complaints are handled by Water Supply & Sewerage.'),
      (('streetlight','street light','electricity','lamp','ಬೀದಿ ದೀಪ','ವಿದ್ಯುತ್'),'Streetlight and electricity complaints are handled by Electricity Utility.'),
      (('drain','flood','flooding','stagnant water','drainage','ಚರಂಡಿ','ಪ್ರವಾಹ'),'Drainage, flooding and stagnant-water complaints are handled by Storm Water Drainage.'),
      (('upload','photo','image','video','evidence','attachment','ಫೋಟೋ','ವೀಡಿಯೊ'),f'Janasetu accepts up to {MAX_IMAGES_PER_COMPLAINT} images (max {MAX_IMAGE_BYTES//1024//1024} MB each) and {MAX_VIDEOS_PER_COMPLAINT} video up to {MAX_VIDEO_SECONDS} seconds (max {MAX_VIDEO_BYTES//1024//1024} MB). Location can come from your map/GPS or image EXIF when available.'),
      (('track','status','my complaint','complaint status','ಸ್ಥಿತಿ'),'Open My Complaints to view the current status, timeline, department updates, evidence and resolution details for your cases.')]
    for keys,answer in mapping:
        if any(k in q for k in keys): return answer
    return 'I can help with Janasetu complaint categories, departments, evidence uploads, location, tracking, priorities and resolution. For live case details, open My Complaints or the GIS/queue page.'

def normalize_phone(phone):
    p=re.sub(r'[^0-9+]','',phone or '')
    if p.startswith('+91'): return p
    if p.startswith('91') and len(p)==12: return '+'+p
    if len(re.sub(r'\D','',p))==10: return '+91'+re.sub(r'\D','',p)
    return p

def valid_indian_phone(phone):
    p=normalize_phone(phone)
    return bool(re.fullmatch(r'\+91[6-9]\d{9}',p))

def otp_hash(code): return generate_password_hash(code)

def create_otp(channel,destination):
    code=f'{secrets.randbelow(1000000):06d}'
    now=utcnow(); exp=now+timedelta(seconds=OTP_TTL_SECONDS)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE otp_verifications SET verified=TRUE WHERE channel=%s AND destination=%s AND verified=FALSE",(channel,destination))
        cur.execute("INSERT INTO otp_verifications(channel,destination,otp_hash,expires_at) VALUES (%s,%s,%s,%s)",(channel,destination,otp_hash(code),exp)); conn.commit()
    return code, exp

def send_email_otp(email,code):
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        return False, 'SMTP is not configured'
    msg=f"From: {SMTP_FROM}\r\nTo: {email}\r\nSubject: Janasetu email verification OTP\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nYour Janasetu verification code is {code}. It expires in {OTP_TTL_SECONDS//60} minutes. Do not share this code."
    try:
        ctx=ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as server:
            server.starttls(context=ctx)
            server.login(SMTP_USERNAME,SMTP_PASSWORD)
            server.sendmail(SMTP_FROM or SMTP_USERNAME,email,msg)
        return True, None
    except Exception as e:
        return False, f'Email provider error: {str(e)[:180]}'

def send_sms_otp(phone,code):
    if not OTP_API_KEY: return False, 'OTP_API_KEY is not configured'
    mobile=normalize_phone(phone)
    if OTP_PROVIDER=='2factor':
        try:
            # Current 2Factor REST OTP API: API key in X-API-Key header.
            if OTP_API_MODE == 'v4':
                payload={'to': mobile, 'template_name': OTP_TEMPLATE_NAME, 'var1': code}
                r=requests.post(OTP_API_URL,headers={'X-API-Key':OTP_API_KEY,'Content-Type':'application/json'},json=payload,timeout=15)
                data=r.json() if 'application/json' in r.headers.get('content-type','').lower() else {}
                ok=r.ok and str(data.get('status','')).lower() in ('sent','success','ok')
                return ok, None if ok else (str(data)[:220] or r.text[:220])
            # Backward-compatible legacy 2Factor endpoint.
            url=f'https://2factor.in/API/V1/{OTP_API_KEY}/SMS/{mobile.replace("+","")}/{code}/Janasetu'
            r=requests.get(url,timeout=15)
            data=r.json() if r.text else {}
            ok=r.ok and str(data.get('Status','')).lower()=='success'
            return ok, None if ok else r.text[:220]
        except Exception as e: return False,f'SMS provider error: {str(e)[:180]}'
    return False,'Unsupported OTP_PROVIDER'

def send_otp(channel,destination):
    code,_=create_otp(channel,destination)
    # Development mode never contacts an external provider.
    if DEV_OTP:
        print(f'[DEV OTP] {channel}: {destination} -> {code}')
        return True, code, None
    if channel=='email': ok,err=send_email_otp(destination,code)
    else: ok,err=send_sms_otp(destination,code)
    if ok: return True, None, None
    return False,None,err

def verify_otp(channel,destination,code):
    rec=one("SELECT id,otp_hash,expires_at,attempts,verified FROM otp_verifications WHERE channel=%s AND destination=%s ORDER BY created_at DESC LIMIT 1",(channel,destination))
    if not rec: return False,'No OTP requested.'
    if rec['verified']: return False,'OTP already used.'
    if rec['expires_at'] < utcnow(): return False,'OTP expired. Please request a new code.'
    if rec['attempts'] >= OTP_MAX_ATTEMPTS: return False,'Too many attempts. Please request a new OTP.'
    execute('UPDATE otp_verifications SET attempts=attempts+1 WHERE id=%s',(rec['id'],))
    if not check_password_hash(rec['otp_hash'],str(code).strip()): return False,'Invalid OTP.'
    execute('UPDATE otp_verifications SET verified=TRUE WHERE id=%s',(rec['id'],)); return True,None

def next_citizen_id():
    r=one("SELECT COALESCE(MAX(CAST(SUBSTRING(citizen_id FROM 5) AS INTEGER)),0)+1 AS n FROM citizens WHERE citizen_id ~ '^CIT-[0-9]+$'")
    return f"CIT-{int(r['n']):04d}"

@app.route('/')
def home(): return render_template('index.html') if current_user() else redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='GET': return render_template('login.html')
    data=request.form if request.form else (request.json or {})
    uid=str(data.get('user_id','')).strip().lower(); pwd=str(data.get('password',''))
    u=one("""SELECT u.user_id,u.email,u.role,u.password_hash,u.citizen_id,u.officer_id,c.name citizen_name,c.ward,c.district,
             o.name officer_name,o.department_id,d.name department FROM users u
             LEFT JOIN citizens c ON c.citizen_id=u.citizen_id LEFT JOIN officers o ON o.officer_id=u.officer_id
             LEFT JOIN departments d ON d.department_id=o.department_id WHERE (LOWER(u.user_id)=%s OR LOWER(u.email)=%s) AND u.is_active=TRUE""",(uid,uid))
    if not u or not check_password_hash(u['password_hash'],pwd):
        return (render_template('login.html',error='Invalid email or password.'),401) if request.form else (jsonify(error='Invalid credentials'),401)
    user={k:u.get(k) for k in ['user_id','email','role','citizen_id','officer_id','citizen_name','ward','district','officer_name','department_id','department']}
    session['user']=user; execute('UPDATE users SET last_login=NOW() WHERE user_id=%s',(u['user_id'],)); log(user['role'],user['user_id'],'Logged in')
    return redirect(url_for('home')) if request.form else jsonify(ok=True,user=user)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='GET': return render_template('register.html', allow_unverified=ALLOW_UNVERIFIED_REGISTRATION)
    data=request.form if request.form else (request.json or {})
    name=str(data.get('name','')).strip(); email=str(data.get('email','')).strip().lower(); phone=normalize_phone(str(data.get('phone','')).strip())
    pwd=str(data.get('password','')); district=str(data.get('district','Bengaluru Urban')).strip(); ward=str(data.get('ward','')).strip(); address=str(data.get('address','')).strip(); lang=str(data.get('language','en'))
    if len(name)<2 or '@' not in email or len(pwd)<8 or not valid_indian_phone(phone):
        msg='Enter a valid name, email, Indian mobile number and a password of at least 8 characters.'
        return (render_template('register.html',error=msg,allow_unverified=ALLOW_UNVERIFIED_REGISTRATION),400) if request.form else (jsonify(error=msg),400)
    if one('SELECT 1 FROM users WHERE LOWER(email)=%s',(email,)) or one('SELECT 1 FROM citizens WHERE phone=%s',(phone,)):
        msg='An account with this email or mobile number already exists.'
        return (render_template('register.html',error=msg,allow_unverified=ALLOW_UNVERIFIED_REGISTRATION),409) if request.form else (jsonify(error=msg),409)
    skip_otp = str(data.get('skip_otp','')).lower() in ('1','true','yes','on')
    password_hash=generate_password_hash(pwd)
    session['pending_registration']={'name':name,'email':email,'phone':phone,'password_hash':password_hash,'district':district,'ward':ward,'address':address,'language':lang,'email_verified':False,'phone_verified':False}
    if skip_otp and ALLOW_UNVERIFIED_REGISTRATION:
        return api_register_complete()
    if request.form: return redirect(url_for('register_verify'))
    return jsonify(ok=True,verify_required=True,skip_otp_allowed=ALLOW_UNVERIFIED_REGISTRATION)

@app.route('/register/verify',methods=['GET'])
def register_verify():
    if not session.get('pending_registration'): return redirect(url_for('register'))
    return render_template('register_verify.html')

@app.post('/api/otp/send')
def api_otp_send():
    p=session.get('pending_registration')
    if not p: return jsonify(error='Registration session expired. Start again.'),400
    channel=str((request.json or {}).get('channel','')).lower()
    if channel not in ('email','phone'): return jsonify(error='Choose email or phone.'),400
    destination=p['email'] if channel=='email' else p['phone']
    ok,dev,err=send_otp(channel,destination)
    if not ok: return jsonify(error=f'Unable to send {channel} OTP. {err or "Check provider settings."}'),502
    return jsonify(ok=True,channel=channel,dev_otp=dev if DEV_OTP else None,expires_in=OTP_TTL_SECONDS)

@app.post('/api/otp/verify')
def api_otp_verify():
    p=session.get('pending_registration')
    if not p: return jsonify(error='Registration session expired. Start again.'),400
    data=request.json or {}; channel=str(data.get('channel','')).lower(); code=str(data.get('code','')).strip()
    destination=p['email'] if channel=='email' else p['phone'] if channel=='phone' else ''
    if not destination or not re.fullmatch(r'\d{6}',code): return jsonify(error='Enter the 6-digit OTP.'),400
    ok,err=verify_otp(channel,destination,code)
    if not ok: return jsonify(error=err),400
    p['email_verified' if channel=='email' else 'phone_verified']=True; session['pending_registration']=p
    return jsonify(ok=True,email_verified=p['email_verified'],phone_verified=p['phone_verified'])

@app.post('/api/register/complete')
def api_register_complete():
    p=session.get('pending_registration')
    if not p: return jsonify(error='Registration session expired. Start again.'),400
    verified = bool(p.get('email_verified') and p.get('phone_verified'))
    if not verified and not ALLOW_UNVERIFIED_REGISTRATION:
        return jsonify(error='Verify both email and mobile OTP before creating the account.'),400
    if one('SELECT 1 FROM users WHERE LOWER(email)=%s',(p['email'],)) or one('SELECT 1 FROM citizens WHERE phone=%s',(p['phone'],)):
        return jsonify(error='Email or mobile number is already registered.'),409
    cid=next_citizen_id()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO citizens(citizen_id,name,email,phone,address,district,ward,preferred_language) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(cid,p['name'],p['email'],p['phone'],p['address'],p['district'],p['ward'],p['language']))
        cur.execute("INSERT INTO users(user_id,email,role,password_hash,citizen_id,email_verified,phone_verified) VALUES (%s,%s,'citizen',%s,%s,%s,%s)",(p['email'],p['email'],p['password_hash'],cid,p.get('email_verified',False),p.get('phone_verified',False))); conn.commit()
    log('citizen',p['email'],'Citizen registered '+('and verified' if verified else 'without OTP verification'))
    session.pop('pending_registration',None)
    if request.form:
        return redirect(url_for('login', registered=1))
    return jsonify(ok=True,citizen_id=cid)

@app.route('/logout')
def logout():
    u=current_user();
    if u: log(u['role'],u['user_id'],'Logged out')
    session.clear(); return redirect(url_for('login'))

@app.route('/api/me')
@login_required
def me(): return jsonify(user=current_user())

@app.route('/health')
def health():
    try:
        pg=one("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis') AS enabled")['enabled']
        return jsonify(status='ok',database='postgresql',postgis=pg,model_loaded=model is not None)
    except Exception as e: return jsonify(status='error',detail=str(e)),503

@app.route('/api/summary')
@login_required
def summary():
    u=current_user(); clauses=[]; args=[]
    if u['role']=='citizen': clauses.append('citizen_id=%s'); args.append(u['citizen_id'])
    elif u['role']=='department': clauses.append('department_id=%s'); args.append(u['department_id'])
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    total=one('SELECT COUNT(*) n FROM complaints'+where,args)['n']; join=' AND ' if where else ' WHERE '
    resolved=one('SELECT COUNT(*) n FROM complaints'+where+join+"status='Resolved'",args)['n']
    critical=one('SELECT COUNT(*) n FROM complaints'+where+join+"priority='Critical'",args)['n']
    breach=one('SELECT COUNT(*) n FROM complaints'+where+join+"sla_deadline<NOW() AND status<>'Resolved'",args)['n']
    return jsonify(total=total,open=total-resolved,resolved=resolved,critical=critical,sla_breached=breach)

@app.route('/api/categories')
@login_required
def categories():
    u=current_user(); clauses=[]; args=[]
    if u['role']=='citizen': clauses.append('citizen_id=%s'); args.append(u['citizen_id'])
    elif u['role']=='department': clauses.append('department_id=%s'); args.append(u['department_id'])
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    return jsonify({r['category']:r['n'] for r in rows('SELECT category,COUNT(*) n FROM complaints'+where+' GROUP BY category ORDER BY n DESC',args)})

@app.route('/api/public-overview')
def public_overview():
    return jsonify(wards=rows("SELECT COALESCE(ward,'Unknown') ward,COUNT(*) issues FROM complaints GROUP BY ward ORDER BY issues DESC LIMIT 12"),
                   districts=rows("SELECT COALESCE(district,'Unknown') district,COUNT(*) issues FROM complaints GROUP BY district ORDER BY issues DESC LIMIT 40"),
                   categories=rows('SELECT category,COUNT(*) issues FROM complaints GROUP BY category ORDER BY issues DESC'),
                   departments=rows("""SELECT d.name department,COUNT(c.complaint_id) issues,COUNT(c.complaint_id) FILTER(WHERE c.status='Resolved') resolved
                                     FROM departments d LEFT JOIN complaints c ON c.department_id=d.department_id GROUP BY d.department_id,d.name ORDER BY issues DESC"""))

@app.route('/api/predict',methods=['POST'])
@login_required
def api_predict():
    text=(request.json or {}).get('text','').strip()
    if not text:return jsonify(error='Enter a complaint'),400
    cat,conf,lang=predict(text); return jsonify(category=cat,department=DEPT.get(cat,'Ward Office'),confidence=round(conf*100,1),language=lang)

def complaint_scope_sql(u):
    if u['role']=='citizen': return 'c.citizen_id=%s',[u['citizen_id']]
    if u['role']=='department': return 'c.department_id=%s',[u['department_id']]
    return 'TRUE',[]

@app.route('/api/complaints',methods=['GET'])
@login_required
def complaints():
    u=current_user(); clause,args=complaint_scope_sql(u)
    data=rows("""SELECT c.*,d.name department,ci.name citizen_name,
                 (SELECT COUNT(*) FROM evidence e WHERE e.complaint_id=c.complaint_id) attachment_count
                 FROM complaints c JOIN departments d ON d.department_id=c.department_id JOIN citizens ci ON ci.citizen_id=c.citizen_id
                 WHERE """+clause+" ORDER BY c.updated_at DESC LIMIT 200",args)
    if u['role']=='citizen':
        for r in data:r.pop('citizen_name',None)
    return jsonify(data)

@app.route('/api/complaints',methods=['POST'])
@login_required
def create_complaint():
    u=current_user()
    if u['role']!='citizen': return jsonify(error='Only citizens can submit complaints'),403
    data=request.form if request.form else (request.json or {})
    files=request.files.getlist('attachments') if request.files else []
    count_error=validate_file_counts(files)
    if count_error: return jsonify(error=count_error),400
    text=str(data.get('text','')).strip(); provided_text=bool(text); requested_category=str(data.get('category','')).strip()
    if not text and not files: return jsonify(error='Add a description or at least one image/video/document.'),400
    if requested_category and requested_category not in CATEGORIES: requested_category=''
    if not text and not requested_category: return jsonify(error='When submitting media without a description, choose the issue category.'),400
    if requested_category: cat=requested_category; conf=1.0 if not text else .95; lang=detect_language(text)
    else: cat,conf,lang=predict(text)
    dep=DEPT.get(cat,'Ward Office'); did=one('SELECT department_id FROM departments WHERE name=%s',(dep,))['department_id']
    if not text: text=f'Media evidence submitted for {cat}.'
    requested_priority=str(data.get('priority','')).strip(); priority=requested_priority if requested_priority in PRIORITIES else ('High' if any(k in text.lower() for k in ['accident','danger','fire','flood','sewage']) else 'Medium')
    try:
        lat=float(data['latitude']) if str(data.get('latitude','')).strip() else None; lng=float(data['longitude']) if str(data.get('longitude','')).strip() else None
    except Exception: return jsonify(error='Invalid latitude/longitude.'),400
    if lat is not None and not (-90<=lat<=90): return jsonify(error='Invalid latitude.'),400
    if lng is not None and not (-180<=lng<=180): return jsonify(error='Invalid longitude.'),400
    ward=str(data.get('ward') or u.get('ward') or 'Unknown'); district=str(data.get('district') or u.get('district') or 'Bengaluru Urban'); address=str(data.get('address','')).strip()
    cid='CL-'+utcnow().strftime('%Y%m%d%H%M%S%f'); sla={'Critical':4,'High':12,'Medium':48,'Low':120}[priority]
    execute("""INSERT INTO complaints(complaint_id,citizen_id,complaint_text,original_language,category,priority,status,department_id,district,ward,address,latitude,longitude,sla_hours,sla_deadline,ai_category_confidence,location_source)
             VALUES (%s,%s,%s,%s,%s,%s,'New',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (cid,u['citizen_id'],text,lang,cat,priority,did,district,ward,address,lat,lng,sla,utcnow()+timedelta(hours=sla),conf,data.get('location_source','manual')))
    if lat is not None and lng is not None: sync_postgis(cid,lat,lng)
    saved=[]; errors=[]
    for f in files:
        item,error=validate_and_save_evidence(f,cid,u['user_id'],'complaint')
        if error: errors.append(error)
        elif item: saved.append(item)
    if errors:
        try:
            execute('DELETE FROM complaints WHERE complaint_id=%s',(cid,)); shutil.rmtree(UPLOAD_ROOT/cid,ignore_errors=True)
        except Exception: pass
        return jsonify(error=' '.join(errors)),400
    if lat is None or lng is None:
        exif_item=next((x for x in saved if x.get('latitude') is not None and x.get('longitude') is not None),None)
        if exif_item:
            lat,lng=exif_item['latitude'],exif_item['longitude']; execute("UPDATE complaints SET latitude=%s,longitude=%s,location_source='evidence_exif' WHERE complaint_id=%s",(lat,lng,cid)); sync_postgis(cid,lat,lng)
        elif not provided_text and saved:
            try:
                execute('DELETE FROM complaints WHERE complaint_id=%s',(cid,)); shutil.rmtree(UPLOAD_ROOT/cid,ignore_errors=True)
            except Exception: pass
            return jsonify(error='Location is required for a media-only complaint. Use current location or pin the issue on the map. GPS-enabled image EXIF is also accepted.'),400
    log('citizen',u['user_id'],'Created complaint',cid)
    return jsonify(complaint_id=cid,category=cat,department=dep,confidence=round(conf*100,1),language=lang,attachments=saved)

@app.route('/api/complaints/<cid>',methods=['PATCH'])
@roles_required('admin','department')
def update_complaint(cid):
    u=current_user(); c=one('SELECT * FROM complaints WHERE complaint_id=%s',(cid,))
    if not c:return jsonify(error='Complaint not found'),404
    if u['role']=='department' and c['department_id']!=u['department_id']:return jsonify(error='Outside your department'),403
    data=request.json or {}; fields=[]; args=[]; new_status=data.get('status')
    if new_status in STATUSES:
        fields.append('status=%s'); args.append(new_status)
        if new_status=='Resolved': fields.append('resolved_at=COALESCE(resolved_at,NOW())')
    if data.get('priority') in PRIORITIES: fields.append('priority=%s'); args.append(data['priority'])
    if fields:
        args.append(cid); execute('UPDATE complaints SET '+','.join(fields)+' WHERE complaint_id=%s',args)
    if data.get('comment') or new_status:
        execute('INSERT INTO complaint_updates(complaint_id,officer_id,status,comment) VALUES (%s,%s,%s,%s)',(cid,u.get('officer_id'),new_status,data.get('comment') or f'Status changed to {new_status}'))
    log(u['role'],u['user_id'],f'Updated {cid}',cid); return jsonify(ok=True)

@app.route('/api/complaints/<cid>/timeline')
@login_required
def complaint_timeline(cid):
    u=current_user(); c=one('SELECT complaint_id,citizen_id,department_id FROM complaints WHERE complaint_id=%s',(cid,))
    if not c:return jsonify(error='Complaint not found'),404
    if u['role']=='citizen' and c['citizen_id']!=u['citizen_id']:return jsonify(error='Forbidden'),403
    if u['role']=='department' and c['department_id']!=u['department_id']:return jsonify(error='Forbidden'),403
    updates=rows('''SELECT cu.update_id,cu.status,cu.comment,cu.timestamp,o.name officer_name
                    FROM complaint_updates cu LEFT JOIN officers o ON o.officer_id=cu.officer_id
                    WHERE cu.complaint_id=%s ORDER BY cu.timestamp ASC''',(cid,))
    audits=[]
    if u['role']=='admin': audits=rows('SELECT action,user_role,user_id,timestamp FROM audit_logs WHERE complaint_id=%s ORDER BY timestamp ASC',(cid,))
    return jsonify(updates=updates,audit=audits)

@app.route('/api/complaints/<cid>/evidence')
@login_required
def complaint_evidence(cid):
    u=current_user(); c=one('SELECT complaint_id,citizen_id,department_id FROM complaints WHERE complaint_id=%s',(cid,))
    if not c:return jsonify(error='Complaint not found'),404
    if u['role']=='citizen' and c['citizen_id']!=u['citizen_id']:return jsonify(error='Forbidden'),403
    if u['role']=='department' and c['department_id']!=u['department_id']:return jsonify(error='Forbidden'),403
    return jsonify(rows("""SELECT evidence_id,original_name,mime_type,file_size,media_type,purpose,uploaded_by,created_at,
                     latitude,longitude,captured_at,duration_seconds,width,height,validation_status,thumbnail_url
                     FROM evidence WHERE complaint_id=%s ORDER BY created_at ASC""",(cid,)))

@app.route('/api/complaints/<cid>/resolve',methods=['POST'])
@roles_required('admin','department')
def resolve_complaint(cid):
    u=current_user(); c=one('SELECT * FROM complaints WHERE complaint_id=%s',(cid,))
    if not c:return jsonify(error='Complaint not found'),404
    if u['role']=='department' and c['department_id']!=u['department_id']:return jsonify(error='Outside your department'),403
    data=request.form
    resolution=str(data.get('resolution','')).strip(); action=str(data.get('action','')).strip(); remarks=str(data.get('remarks','')).strip()
    if len(resolution)<5:return jsonify(error='Please provide a meaningful resolution description.'),400
    execute("UPDATE complaints SET status='Resolved',resolved_at=NOW(),resolution_text=%s,resolution_action=%s,resolution_remarks=%s,resolution_by=%s WHERE complaint_id=%s",(resolution,action,remarks,u.get('officer_name') or 'Administrator',cid))
    execute('INSERT INTO complaint_updates(complaint_id,officer_id,status,comment) VALUES (%s,%s,%s,%s)',(cid,u.get('officer_id'),'Resolved',resolution))
    saved=[]
    resolution_files=request.files.getlist('resolution_files')
    count_error=validate_file_counts(resolution_files)
    if count_error: return jsonify(error=count_error),400
    for f in resolution_files:
        item,error=validate_and_save_evidence(f,cid,u['user_id'],'resolution')
        if error: return jsonify(error=error),400
        if item: saved.append(item)
    log(u['role'],u['user_id'],f'Resolved {cid}',cid)
    return jsonify(ok=True,complaint_id=cid,status='Resolved',resolution_files=saved)

@app.route('/api/evidence/<int:eid>')
@login_required
def evidence_file(eid):
    e=one('SELECT e.*,c.citizen_id,c.department_id FROM evidence e JOIN complaints c ON c.complaint_id=e.complaint_id WHERE e.evidence_id=%s',(eid,))
    if not e: abort(404)
    u=current_user(); allowed=u['role']=='admin' or (u['role']=='citizen' and e['citizen_id']==u['citizen_id']) or (u['role']=='department' and e['department_id']==u['department_id'])
    if not allowed: abort(403)
    return send_file(BASE/e['file_url'],download_name=e['original_name'],as_attachment=False)

@app.route('/api/evidence/<int:eid>/thumbnail')
@login_required
def evidence_thumbnail(eid):
    e=one('SELECT e.thumbnail_url,c.citizen_id,c.department_id FROM evidence e JOIN complaints c ON c.complaint_id=e.complaint_id WHERE e.evidence_id=%s',(eid,))
    if not e or not e.get('thumbnail_url'): abort(404)
    u=current_user(); allowed=u['role']=='admin' or (u['role']=='citizen' and e['citizen_id']==u['citizen_id']) or (u['role']=='department' and e['department_id']==u['department_id'])
    if not allowed: abort(403)
    return send_file(BASE/e['thumbnail_url'],mimetype='image/jpeg',as_attachment=False)

@app.route('/api/map/public')
def public_map():
    # Rounded aggregation protects exact household locations.
    data=rows("""SELECT ROUND(latitude::numeric,2)::float lat,ROUND(longitude::numeric,2)::float lng,COUNT(*) count,
                 MODE() WITHIN GROUP (ORDER BY category) category,
                 MODE() WITHIN GROUP (ORDER BY district) district
                 FROM complaints WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                 GROUP BY ROUND(latitude::numeric,2),ROUND(longitude::numeric,2) ORDER BY count DESC LIMIT 500""")
    return jsonify(data)

@app.route('/api/map/complaints')
@login_required
def map_complaints():
    u=current_user(); clause,args=complaint_scope_sql(u)
    data=rows("""SELECT c.complaint_id,c.category,c.priority,c.status,c.ward,c.district,c.latitude lat,c.longitude lng,d.name department
                 FROM complaints c JOIN departments d ON d.department_id=c.department_id
                 WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL AND """+clause+" ORDER BY c.created_at DESC LIMIT 3000",args)
    return jsonify(data)

@app.route('/api/map/hotspots')
@roles_required('admin','department')
def hotspots():
    u=current_user(); clause,args=complaint_scope_sql(u)
    data=rows("""SELECT ROUND(c.latitude::numeric,2)::float lat,ROUND(c.longitude::numeric,2)::float lng,COUNT(*) count,
                 MODE() WITHIN GROUP (ORDER BY c.category) category,COUNT(*) FILTER(WHERE c.priority IN ('Critical','High')) high_risk
                 FROM complaints c WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL AND """+clause+
              " GROUP BY ROUND(c.latitude::numeric,2),ROUND(c.longitude::numeric,2) HAVING COUNT(*)>=1 ORDER BY count DESC LIMIT 100",args)
    return jsonify(data)

@app.route('/api/map/district-summary')
@roles_required('admin','department')
def district_summary():
    u=current_user(); clause,args=complaint_scope_sql(u)
    data=rows("""SELECT COALESCE(c.district,'Unknown') district,COUNT(*) count,
                 COUNT(*) FILTER(WHERE c.priority IN ('Critical','High')) high_risk,
                 COUNT(*) FILTER(WHERE c.status='Resolved') resolved
                 FROM complaints c WHERE """+clause+
              " GROUP BY COALESCE(c.district,'Unknown') ORDER BY count DESC LIMIT 40",args)
    return jsonify(data)

@app.route('/api/citizens')
@roles_required('admin')
def citizens(): return jsonify(rows("SELECT citizen_id,name,email,phone,district,ward,created_at,(SELECT COUNT(*) FROM complaints c WHERE c.citizen_id=citizens.citizen_id) complaints FROM citizens ORDER BY created_at DESC"))
@app.route('/api/officers')
@roles_required('admin')
def officers(): return jsonify(rows('SELECT o.*,d.name department FROM officers o JOIN departments d ON d.department_id=o.department_id ORDER BY d.name,o.name'))
@app.route('/api/departments')
@roles_required('admin')
def departments(): return jsonify(rows('SELECT * FROM departments ORDER BY name'))

@app.route('/api/officers',methods=['POST'])
@roles_required('admin')
def create_officer():
    data=request.json or {}; name=str(data.get('name','')).strip(); email=str(data.get('email','')).lower().strip(); pwd=str(data.get('password','')); did=data.get('department_id')
    if not name or '@' not in email or len(pwd)<8 or not did:return jsonify(error='Name, valid email, department and 8+ character password are required.'),400
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO officers(name,email,department_id) VALUES (%s,%s,%s) RETURNING officer_id',(name,email,did)); oid=cur.fetchone()['officer_id']
        cur.execute("INSERT INTO users(user_id,email,role,password_hash,officer_id) VALUES (%s,%s,'department',%s,%s)",(email,email,generate_password_hash(pwd),oid)); conn.commit()
    log('admin',current_user()['user_id'],f'Created department officer {email}'); return jsonify(ok=True)

@app.route('/api/department-performance')
@roles_required('admin')
def dept_perf(): return jsonify(rows("""SELECT d.name department,COUNT(c.complaint_id) total,COUNT(c.complaint_id) FILTER(WHERE c.status<>'Resolved') open,
    COUNT(c.complaint_id) FILTER(WHERE c.status='Resolved') resolved,COUNT(c.complaint_id) FILTER(WHERE c.sla_deadline<NOW() AND c.status<>'Resolved') breached,
    ROUND(100.0*COUNT(c.complaint_id) FILTER(WHERE c.status='Resolved')/NULLIF(COUNT(c.complaint_id),0),1) resolution_rate
    FROM departments d LEFT JOIN complaints c ON c.department_id=d.department_id GROUP BY d.department_id,d.name ORDER BY breached DESC"""))
@app.route('/api/audit')
@roles_required('admin')
def audit(): return jsonify(rows('SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 200'))

@app.route('/api/ai/status')
@login_required
def ai_status():
    base=os.getenv('OLLAMA_BASE_URL',os.getenv('OLLAMA_HOST','http://localhost:11434')).rstrip('/')
    try:
        tags=requests.get(base+'/api/tags',timeout=2.5); tags.raise_for_status(); installed=[m.get('name','') for m in tags.json().get('models',[]) if m.get('name')]
        fast_order=['qwen3:0.6b','gemma3:1b','llama3.2:1b','qwen3:1.7b','qwen3:4b']
        selected=next((m for pref in fast_order for m in installed if m==pref or m.startswith(pref+':')),installed[0] if installed else None)
        return jsonify(ok=True,ollama=True,models=installed,selected_model=selected,recommended_model='qwen3:0.6b',fast_mode=True)
    except Exception:
        return jsonify(ok=True,ollama=False,models=[],selected_model=None,recommended_model='qwen3:0.6b',fast_mode=True)

@app.route('/api/ai/ask',methods=['POST'])
@login_required
def ai_ask():
    data=request.json or {}; question=str(data.get('question','')).strip()
    if len(question)<2: return jsonify(ok=False,error='Ask a complete question.'),400
    quick_answer=_fallback_ai_answer(question); q=question.lower()
    quick_keys=('pothole','potholes','road','footpath','garbage','waste','dumping','water','streetlight','electricity','drain','flood','upload','photo','image','video','evidence','attachment','track','status','ಗುಂಡಿ','ರಸ್ತೆ','ಕಸ','ನೀರು','ಬೀದಿ ದೀಪ','ವೀಡಿಯೊ','ಫೋಟೋ','ಸ್ಥಿತಿ')
    if any(k in q for k in quick_keys): return jsonify(ok=True,answer=quick_answer,model='Janasetu instant civic engine',fast_path=True)
    base=os.getenv('OLLAMA_BASE_URL',os.getenv('OLLAMA_HOST','http://localhost:11434')).rstrip('/'); configured=os.getenv('AI_FAST_MODEL','qwen3:0.6b'); timeout=max(8,min(45,int(os.getenv('AI_TIMEOUT_SECONDS','25'))))
    system='You are Janasetu AI, a concise Karnataka civic-services assistant. Answer only about complaint registration, departments, location/GIS, evidence, priorities, SLA/status and resolution. Never invent policy, phone numbers or legal claims. For live case data tell the user which Janasetu page to open. Support English and Kannada. Answer in 1-3 short sentences.'
    try:
        tags=requests.get(base+'/api/tags',timeout=2.5); tags.raise_for_status(); installed=[m.get('name','') for m in tags.json().get('models',[]) if m.get('name')]
        order=[configured,'qwen3:0.6b','gemma3:1b','llama3.2:1b','qwen3:1.7b',os.getenv('OLLAMA_LLM_MODEL','qwen3:4b')]
        model=next((m for pref in order for m in installed if m==pref or m.startswith(pref+':')),installed[0] if installed else None)
        if not model: return jsonify(ok=True,answer=quick_answer,model='Janasetu fallback',fast_path=True,warning='No Ollama model installed. For fast local AI run: ollama pull qwen3:0.6b')
        payload={'model':model,'stream':False,'think':False,'keep_alive':'20m','messages':[{'role':'system','content':system},{'role':'user','content':question}],'options':{'temperature':0.1,'num_predict':96,'num_ctx':1024}}
        r=requests.post(base+'/api/chat',json=payload,timeout=timeout); r.raise_for_status(); body=r.json(); answer=((body.get('message') or {}).get('content') or body.get('response') or '').strip()
        if not answer: return jsonify(ok=True,answer=quick_answer,model='Janasetu fallback',fast_path=True,warning='Local model returned an empty response.')
        return jsonify(ok=True,answer=answer,model=model,fast_path=False)
    except (requests.exceptions.ConnectionError,requests.exceptions.Timeout):
        return jsonify(ok=True,answer=quick_answer,model='Janasetu fallback',fast_path=True,warning='Local model was unavailable/slow; returned an instant Janasetu answer instead.')
    except Exception as e:
        return jsonify(ok=True,answer=quick_answer,model='Janasetu fallback',fast_path=True,warning=str(e)[:180])

if __name__=='__main__':
    init_db(seed=os.getenv('SEED_DEMO_DATA','true').lower()=='true')
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG','0')=='1')
