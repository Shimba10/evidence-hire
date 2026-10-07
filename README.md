# EvidenceHire MVP

Evidence-based technical hiring MVP.

## What it does
1. Recruiter pastes a job description and uploads a candidate resume (PDF/DOCX/TXT).
2. Backend extracts text and asks Gemini to turn the JD + resume into structured requirements, candidate claims, and evidence gaps.
3. Recruiter launches an adaptive technical interview.
4. Each candidate answer is evaluated against the relevant skill and used to generate the next question.
5. Final report separates **claims**, **demonstrated evidence**, **confidence**, and **remaining uncertainty**.

## Stack
- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL in production; SQLite locally
- AI: Google Gemini via `google-genai` SDK. Default model is `gemini-2.5-flash-lite`; change `GEMINI_MODEL` if your Google AI Studio account exposes another model.
- Frontend deploy: Vercel
- Backend deploy: Railway

## Local development

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put GEMINI_API_KEY in .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_URL=http://localhost:8000` for local use.

## Railway
Create a Railway project with:
- one PostgreSQL service
- one backend service connected to this repo, with root directory `backend`

Set:
- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-2.5-flash-lite`
- `DATABASE_URL` from Railway Postgres (Railway may provide this automatically when referenced)
- `FRONTEND_ORIGIN=https://YOUR-VERCEL-DOMAIN.vercel.app`

Railway start command is defined in `railway.toml`.

## Vercel
Import the repo into Vercel and set the project root to `frontend`.
Set:
- `VITE_API_URL=https://YOUR-RAILWAY-DOMAIN.up.railway.app`

## Important MVP limitations
- No authentication/authorization yet.
- No GitHub/code repository verification yet.
- No ATS integrations.
- AI assessment is decision support, not an automated employment decision.
- Do not use protected characteristics or unrelated personal information in scoring.
- Add consent, retention/deletion controls, audit logs, and human review before production use.
