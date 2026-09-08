# Janasetu — AI-Powered Civic Intelligence & Grievance Management Platform

> **Janasetu (ಜನಸೇತು)** — *A Bridge for the People*

Janasetu is a full-stack civic intelligence platform designed to connect citizens, government departments and administrators through **AI-assisted grievance processing, geospatial intelligence, multimodal evidence handling and transparent resolution workflows**.

The platform is designed for smart-city and e-governance use cases where a complaint is not merely a text record, but a structured civic event containing **what happened, where it happened, visual/document evidence, responsible department, priority and resolution history**.

---

## 1. Project Objective

Conventional grievance systems usually follow:

```text
Citizen → Complaint Form → Department → Status
```

Janasetu extends this into an intelligent workflow:

```text
Citizen
   │
   ├── Natural-language complaint
   ├── Location
   ├── Images
   ├── Video
   └── Documents
          │
          ▼
   Civic Intelligence Layer
          │
          ├── AI understanding
          ├── Category / department reasoning
          ├── Priority assistance
          ├── Evidence metadata
          └── Location intelligence
          │
          ▼
   Department Workflow
          │
          ├── Review
          ├── Investigation
          ├── Action
          └── Resolution evidence
          │
          ▼
        Citizen
```

The goal is to reduce manual interpretation, improve routing, preserve evidence, and make the complete complaint lifecycle more transparent.

---

# 2. Why AI Is Important in Janasetu

AI is not included merely as a chatbot. It is intended to act as an **intelligence layer around civic data and workflows**.

A citizen may write:

> "There is a huge pothole near the school and vehicles are struggling to pass."

A conventional application stores this as a text field.

Janasetu can use an LLM to understand concepts such as:

```text
Problem type  → Road / pothole
Potential department → Roads / Infrastructure
Context       → Near school
Impact        → Vehicle accessibility / safety
Potential priority → High
```

This creates structured information that can support downstream workflows.

## AI provides five major benefits

### 2.1 Natural-language understanding

Citizens do not need to know official government terminology.

They can describe a problem naturally, and the AI assistant can explain relevant civic procedures and departments.

### 2.2 Department assistance

AI can help map an unstructured complaint to a likely civic domain.

Example:

```text
"Street light has been off for three days"
              ↓
Infrastructure issue
              ↓
Street Lighting / Electrical Department
```

The final department decision should remain configurable and auditable rather than blindly trusting the model.

### 2.3 Priority assistance

AI can identify signals such as:

- public safety risk
- blocked roads
- water contamination
- major drainage overflow
- repeated infrastructure failure
- proximity to sensitive locations

AI-generated priority should be treated as **decision support**, not an irreversible government decision.

### 2.4 Citizen assistance

The local AI assistant can answer questions such as:

```text
Who handles pothole complaints?

What evidence should I upload?

How do I track my complaint?

What information is required for a drainage complaint?
```

### 2.5 Administrative intelligence

Structured complaint data can later support:

- hotspot detection
- category trends
- recurring issue analysis
- department workload analysis
- SLA monitoring
- geographic prioritization
- duplicate complaint detection

---
# Janasetu

[Your existing introduction]

## Project Overview

[Your existing correct content]

## 📸 Product Walkthrough

### 1. Citizen Experience
![Citizen Login](docs/Screrenshots/LOGIN.png)

### 2. Citizen Dashboard
![Citizen Dashboard](docs/Screrenshots/DASHBOARD.png)

### 3. Complaint Submission
![Raise Complaint](docs/Screrenshots/RAISE-COMPLAINT.png)

### 4. Karnataka GIS
![GIS](docs/Screrenshots/MAP.png)

### 5. Department Workflow
![Department](docs/Screrenshots/DEPARTMENT.png)

### 6. AI Assistant
![AI Assistant](docs/Screrenshots/AI.png)

# 3. LLM Implementation

Janasetu uses a **local Large Language Model (LLM)** through Ollama.

Recommended model:

```text
Qwen3 0.6B
```

The lightweight model is selected primarily for **low-latency local inference** and easier deployment on consumer hardware.

## LLM Architecture

```text
                User
                 │
                 ▼
        Civic Assistant UI
                 │
                 ▼
          Flask API Layer
                 │
                 ├── Prompt construction
                 ├── Context selection
                 ├── Request validation
                 └── Timeout handling
                 │
                 ▼
              Ollama
                 │
                 ▼
             Qwen3
                 │
                 ▼
        Generated response
                 │
                 ▼
              Citizen
```

## Local inference

Ollama runs locally:

```text
http://localhost:11434
```

Example environment configuration:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen3:0.6b
AI_FAST_MODEL=qwen3:0.6b
AI_TIMEOUT_SECONDS=25
```

This avoids requiring a paid cloud LLM API for local development.

---

# 4. Why a Local LLM?

For a civic application, local inference provides several architectural advantages.

### Privacy

Citizen complaints can contain:

- addresses
- phone numbers
- photographs
- documents
- location information

Keeping inference local reduces the need to transmit complaint content to an external AI provider.

### Cost

Local inference does not require per-request cloud LLM billing.

### Availability

The AI service can continue to work without dependence on an external LLM API, provided the local machine has the model installed.

### Demonstration

The complete AI pipeline can be demonstrated on a local machine without requiring a commercial AI API key.

---

# 5. Fast AI Architecture

Large models can be slow on CPU-only machines.

Janasetu therefore supports a lightweight model for fast civic-assistant responses:

```text
AI_FAST_MODEL=qwen3:0.6b
```

The system is designed so that AI failure does not prevent the core grievance-management application from operating.

Conceptually:

```text
AI available
    ↓
Generate intelligent response

AI unavailable / timeout
    ↓
Return controlled fallback
    ↓
Core complaint system continues
```

This is important because **AI should be an enhancement to civic infrastructure, not a single point of failure**.

---

# 6. RAG Architecture Decision

The current implementation intentionally does **not require Retrieval-Augmented Generation (RAG)**.

Earlier designs used:

```text
Documents
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector database
    ↓
Similarity retrieval
    ↓
Prompt
    ↓
LLM
```

RAG is powerful when the system must answer questions from a large changing document collection.

However, it introduced additional infrastructure and operational complexity for the current Janasetu use case.

The current design therefore uses:

```text
Application Context
        +
Structured Civic Data
        +
Prompt Engineering
        ↓
       LLM
```

## Why this is useful

It removes dependencies such as:

- ChromaDB startup
- embedding model initialization
- vector-index synchronization
- document ingestion pipelines
- vector-store corruption/version problems

This improves:

- startup reliability
- deployment simplicity
- local development
- debugging
- response predictability

## Future RAG option

RAG can be reintroduced later for authoritative government knowledge such as:

- municipal regulations
- government circulars
- department procedures
- service-level agreements
- official schemes
- Kannada government documents

A future architecture could be:

```text
Official Government Documents
            ↓
       Text extraction
            ↓
         Chunking
            ↓
        Embeddings
            ↓
      Vector Database
            ↓
       Relevant Context
            ↓
      Local / Cloud LLM
```

This should be added only when the project has a sufficiently large and authoritative knowledge base.

---

# 7. Multimodal Evidence Architecture

Civic complaints are inherently multimodal.

A citizen may have:

```text
Text only
Image only
Video only
Text + image
Text + video
Text + image + video
Text + document
```

Janasetu therefore treats evidence as a separate complaint component.

```text
Complaint
   │
   ├── Text
   ├── Location
   └── Evidence
         ├── Images
         ├── Video
         └── Documents
```

## Image evidence

Images can provide direct visual proof of:

- potholes
- garbage
- damaged infrastructure
- drainage overflow
- broken streetlights
- road damage

Configured limit:

```env
MAX_IMAGE_MB=10
MAX_IMAGES_PER_COMPLAINT=5
```

## Video evidence

Video is useful when the problem is dynamic.

Examples:

- overflowing water
- traffic obstruction
- drainage flow
- repeated streetlight malfunction
- garbage collection failure

Configured limit:

```env
MAX_VIDEO_MB=100
MAX_VIDEO_SECONDS=60
MAX_VIDEOS_PER_COMPLAINT=1
```

A new AI model is **not required simply to accept a video**. The application can store, validate and associate the video with the complaint.

Future versions can extract video frames and apply computer-vision models.

## Document evidence

Documents may include:

- notices
- scanned records
- supporting correspondence
- civic documents

Configured limit:

```env
MAX_DOCUMENT_MB=20
```

---

# 8. Evidence + Location Intelligence

A particularly important feature is combining evidence with geographic information.

Example:

```text
Complaint:
Pothole

District:
Bengaluru Urban

Taluk:
Anekal

Latitude:
12.xxxxxx

Longitude:
77.xxxxxx

Evidence:
3 photographs
1 video
```

This allows administrators to investigate both:

```text
WHAT happened?
```

and:

```text
WHERE did it happen?
```

---

# 9. Karnataka GIS Architecture

Janasetu is designed around Karnataka administrative geography.

Conceptual hierarchy:

```text
Karnataka
   │
   ├── District
   │      │
   │      └── Taluk
   │              │
   │              └── Complaint
   │
   └── Geographic statistics
```

GIS functionality can support:

- district visualization
- taluk boundaries
- complaint locations
- district-level case counts
- geographic filtering
- complaint density
- hotspot analysis

When a district is selected, the interface can display:

```text
District name
Total cases
Open cases
In-progress cases
Resolved cases
Complaint categories
Complaint locations
```

---

# 10. Complaint Lifecycle

```text
SUBMITTED
    ↓
REGISTERED
    ↓
UNDER REVIEW
    ↓
ASSIGNED
    ↓
INVESTIGATION
    ↓
ACTION TAKEN
    ↓
RESOLVED
```

Every transition can be associated with relevant timestamps and information.

---

# 11. Department Workflow

The platform separates the citizen experience from the department experience.

Department users can receive:

- complaint description
- location
- category
- evidence
- citizen-provided information
- status history

The department can then:

1. Review the complaint
2. Inspect evidence
3. Investigate the location
4. Record action
5. Upload resolution evidence
6. Update resolution notes
7. Close the complaint

---

# 12. Resolution Transparency

Resolution should not simply mean:

```text
Status = Resolved
```

A meaningful resolution can contain:

```text
Status:
RESOLVED

Department:
Roads & Infrastructure

Action:
Pothole repaired

Resolution date:
08-09-2026

Resolution notes:
Road surface repaired and inspected.

Resolution evidence:
Repair photograph
```

The citizen can then see the relevant resolution information.

This improves:

- transparency
- accountability
- citizen trust
- auditability

---

# 13. Authentication

Janasetu supports:

```text
Citizen Registration
       ↓
Email Verification
       +
Mobile Verification
       ↓
Citizen Account
```

External OTP services are optional infrastructure rather than an AI dependency.

## Email OTP

SMTP can be configured using:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=YOUR_EMAIL
SMTP_PASSWORD=YOUR_APP_PASSWORD
SMTP_FROM=YOUR_EMAIL
```

## SMS OTP

An Indian SMS OTP provider such as 2Factor can be configured:

```env
OTP_PROVIDER=2factor
OTP_API_KEY=YOUR_API_KEY
```

## Demo authentication

For demonstrations where external services are unavailable:

```env
DEV_OTP=true
```

Controlled OTP-free registration can also be enabled:

```env
ALLOW_UNVERIFIED_REGISTRATION=true
```

These options should normally be disabled in production.

---

# 14. Database Architecture

PostgreSQL is the primary relational database.

Conceptual entities include:

```text
User
Department
Complaint
Complaint Status
Location
Evidence
Resolution
Authentication / Verification
```

Relationships:

```text
User
 │
 └── Complaint
       │
       ├── Location
       ├── Evidence
       ├── Department
       ├── Status History
       └── Resolution
```

---

# 15. PostGIS

PostGIS is an optional spatial extension for PostgreSQL.

It can enable advanced operations such as:

- distance queries
- spatial intersections
- radius searches
- geographic aggregation
- spatial hotspot analysis

The core application can operate without PostGIS where advanced spatial SQL is not required.

---

# 16. AI Safety and Governance

Because Janasetu is a civic system, AI output should be treated as **decision support**.

The LLM should not independently:

- reject legitimate complaints
- make legal determinations
- impose penalties
- make irreversible government decisions
- fabricate official policy

The preferred architecture is:

```text
AI Recommendation
       ↓
Human / Rule Validation
       ↓
Department Decision
```

This keeps government accountability with authorized personnel.

---

# 17. AI Hallucination Control

The assistant should be instructed to:

- avoid inventing department policies
- clearly state uncertainty
- use application-provided context
- avoid claiming actions that did not occur
- avoid fabricating complaint status
- avoid inventing government contact information

For operational data, the backend/database should remain the source of truth.

```text
Complaint status → Database
User identity    → Database
Location         → Database
Resolution       → Database
AI explanation   → LLM
```

The LLM should explain data rather than replace the authoritative data source.

---

# 18. AI vs Traditional Logic

Not every feature needs AI.

Janasetu intentionally separates deterministic application logic from probabilistic AI.

### Use traditional backend logic for:

- authentication
- authorization
- database operations
- complaint IDs
- file-size validation
- allowed file types
- status transitions
- permissions
- audit records

### Use AI for:

- natural-language understanding
- civic question answering
- complaint interpretation
- explanation
- classification assistance
- future summarization
- future multimodal analysis

This hybrid architecture is more reliable than putting every application function behind an LLM.

---

# 19. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python |
| Web Framework | Flask |
| Database | PostgreSQL |
| Spatial Database | Optional PostGIS |
| Frontend | HTML / CSS / JavaScript |
| LLM Runtime | Ollama |
| LLM | Qwen3 |
| AI Mode | Local inference |
| GIS | Interactive web maps |
| Authentication | Session + OTP |
| Evidence | Images / Video / Documents |
| Deployment | Docker / WSGI / Cloud VM |

---

# 20. Environment Configuration

Example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:2003/civiclens
SECRET_KEY=CHANGE_THIS_SECRET

FLASK_DEBUG=0
PORT=5000
SESSION_COOKIE_SECURE=true

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen3:0.6b
AI_FAST_MODEL=qwen3:0.6b
AI_TIMEOUT_SECONDS=25

OTP_PROVIDER=2factor
OTP_API_KEY=YOUR_API_KEY

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=YOUR_EMAIL
SMTP_PASSWORD=YOUR_APP_PASSWORD
SMTP_FROM=YOUR_EMAIL

DEV_OTP=false
ALLOW_UNVERIFIED_REGISTRATION=false

MAX_UPLOAD_MB=180
MAX_IMAGE_MB=10
MAX_VIDEO_MB=100
MAX_DOCUMENT_MB=20
MAX_VIDEO_SECONDS=60
MAX_IMAGES_PER_COMPLAINT=5
MAX_VIDEOS_PER_COMPLAINT=1
MAX_FILES_PER_COMPLAINT=6
```

---

# 21. Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/janasetu-civic-intelligence-platform.git
cd janasetu-civic-intelligence-platform
```

Create environment:

```bash
python -m venv .venv
```

Windows:

```cmd
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the local LLM:

```bash
ollama pull qwen3:0.6b
```

Configure `.env`.

Start the application:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 22. Production Architecture

```text
                    Internet
                       │
                       ▼
                Reverse Proxy
                       │
                       ▼
                WSGI Server
                       │
                       ▼
              ┌─────────────────┐
              │    Janasetu     │
              │   Flask App     │
              └───────┬─────────┘
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
       PostgreSQL              Ollama
            │                    │
            ▼                    ▼
       Civic Data             Local LLM
```

Production should use:

```env
FLASK_DEBUG=0
DEV_OTP=false
ALLOW_UNVERIFIED_REGISTRATION=false
SESSION_COOKIE_SECURE=true
```

Secrets must be supplied through environment variables or a deployment platform's secret manager.

---

# 23. Security

Never commit:

```text
.env
Database passwords
SMTP passwords
OTP API keys
Secret keys
Production credentials
Citizen personal information
Private uploaded evidence
```

Use:

```text
.env.example
```

for public documentation.

The repository should contain only safe demonstration data and synthetic datasets.

---

# 24. Current AI Capability

```text
Local LLM                         ✅
Ollama integration                ✅
Fast lightweight AI mode         ✅
AI civic assistant                ✅
AI-independent core application  ✅
RAG dependency                   ❌
Vector database dependency       ❌
Embedding dependency             ❌
Cloud LLM API requirement        ❌
```

---

# 25. Future AI Roadmap

## Phase 1 — Current

```text
Local LLM
Civic assistant
Natural-language understanding
Application-context prompting
```

## Phase 2

```text
AI complaint classification
Department recommendation
Priority recommendation
Complaint summarization
Duplicate complaint detection
```

## Phase 3

```text
Computer vision
Image-based issue classification
OCR
Video frame analysis
Multimodal LLM
```

## Phase 4

```text
Government-document RAG
Official policy retrieval
Kannada-English multilingual RAG
Evidence-grounded answers
```

## Phase 5

```text
Predictive civic intelligence
Complaint hotspot prediction
SLA breach prediction
Infrastructure risk prediction
Resource allocation assistance
```

---

# 26. Future Multimodal AI Architecture

For an advanced version:

```text
                  Complaint
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      Text          Image         Video
       │             │             │
       ▼             ▼             ▼
     LLM/NLP     Vision Model   Frame Extraction
       │             │             │
       └─────────────┼─────────────┘
                     ▼
             Multimodal Context
                     │
                     ▼
               Civic AI Layer
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
 Department       Priority       Summary
 Routing          Assistance     / Report
```

A specialized model does **not** need to be introduced merely to support uploads. Specialized AI becomes valuable when the project needs automated interpretation of the media itself.

---

# 27. Example End-to-End Use Case

A citizen records a 40-second video of an overflowing roadside drain.

The complaint contains:

```text
Description:
Drain overflowing onto the road.

Location:
District + Taluk + GPS coordinates

Evidence:
40-second video
2 photographs
```

Janasetu stores the complaint and evidence.

The AI layer can assist with:

```text
Problem:
Drainage overflow

Likely category:
Drainage / Sanitation

Potential priority:
High

Reason:
Overflow is affecting a public road.
```

The responsible department reviews the complaint.

After corrective action:

```text
Status:
RESOLVED

Action:
Drain cleared and overflow stopped.

Resolution evidence:
After-repair photograph
```

The citizen can see the complete resolution.

---

# 28. Project Status

| Component | Status |
|---|---|
| Citizen Portal | ✅ |
| Complaint Management | ✅ |
| Department Workflow | ✅ |
| GIS / Maps | ✅ |
| Karnataka Location Support | ✅ |
| Image Evidence | ✅ |
| Video Evidence | ✅ |
| Document Evidence | ✅ |
| Local LLM | ✅ |
| Fast AI Mode | ✅ |
| Email OTP | ⚙️ SMTP required |
| SMS OTP | ⚙️ Provider API required |
| PostGIS | ⚙️ Optional |
| RAG | ❌ Not required |
| Vector Database | ❌ Not required |
| Production Deployment | ⚙️ Requires environment configuration |

---

# 29. Known Limitations

### SMTP

Email OTP requires correctly configured SMTP credentials.

### SMS

Real mobile OTP requires an external SMS provider and API key.

### PostGIS

Advanced spatial database operations require PostGIS to be installed.

### Local LLM

Inference speed depends on CPU, RAM, GPU and model size.

### AI Accuracy

LLM outputs are probabilistic and must not be treated as authoritative government decisions without validation.

---

# 30. Research and Engineering Value

Janasetu demonstrates the integration of several modern software and AI concepts in one civic application:

- Large Language Models
- Local AI inference
- Human-in-the-loop AI
- Geospatial intelligence
- Multimodal evidence architecture
- Structured civic data
- Workflow automation
- AI-assisted classification
- Secure authentication
- Evidence management
- Spatial analytics
- Transparent resolution tracking

The key engineering principle is that **AI augments the civic workflow rather than replacing deterministic backend systems or government decision-makers**.

---

# 31. Vision

Janasetu aims to evolve civic grievance management from:

> **Submit a complaint and wait.**

into:

> **Report → Understand → Locate → Route → Investigate → Act → Verify → Resolve**

The long-term objective is an intelligent civic infrastructure layer where **citizen-generated information, geographic data, evidence, AI assistance and departmental workflows** work together to improve public-service delivery, transparency and accountability.

---

## GitHub Topics

```text
artificial-intelligence
civic-tech
smart-city
grievance-management
gis
karnataka
india
flask
postgresql
ollama
llm
qwen
machine-learning
geospatial
citizen-services
multimodal-ai
e-governance
```

## Repository Description

> AI-powered civic intelligence platform combining local LLM assistance, Karnataka GIS, multimodal evidence, department workflows, OTP authentication and transparent grievance resolution.
