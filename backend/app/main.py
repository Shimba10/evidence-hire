import io, json, os
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pypdf import PdfReader
from docx import Document
from .db import Base, engine, get_db
from .models import Assessment, Interview
from .schemas import AnswerRequest, InterviewStart
from .ai import AIError, analyze_candidate, first_question, evaluate_turn, next_question, final_report
from .config import settings

Base.metadata.create_all(bind=engine)
app = FastAPI(title="EvidenceHire API", version="0.1.0")

origins = [x.strip() for x in settings.frontend_origin.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if lower.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise HTTPException(400, "Upload a PDF, DOCX, or TXT resume")

@app.get("/health")
def health():
    return {"status": "ok", "ai_configured": bool(settings.gemini_api_key), "model": settings.gemini_model}

@app.post("/api/assessments")
async def create_assessment(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description is too short")
    data = await resume.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "Resume must be under 8MB")
    resume_text = extract_text(resume.filename or "resume.txt", data).strip()
    if len(resume_text) < 100:
        raise HTTPException(400, "Could not extract enough text from the resume")
    try:
        analysis = analyze_candidate(job_description, resume_text)
    except AIError as exc:
        raise HTTPException(502, str(exc))
    assessment = Assessment(
        job_description=job_description,
        resume_text=resume_text,
        candidate_name=analysis.candidate_name,
        analysis_json=analysis.model_dump_json(),
    )
    db.add(assessment)
    db.commit(); db.refresh(assessment)
    return {"id": assessment.id, "analysis": analysis.model_dump()}

@app.get("/api/assessments/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    item = db.get(Assessment, assessment_id)
    if not item: raise HTTPException(404, "Assessment not found")
    return {"id": item.id, "analysis": json.loads(item.analysis_json)}

@app.post("/api/interviews")
def start_interview(payload: InterviewStart, db: Session = Depends(get_db)):
    assessment = db.get(Assessment, payload.assessment_id)
    if not assessment: raise HTTPException(404, "Assessment not found")
    from .schemas import Analysis
    analysis = Analysis.model_validate_json(assessment.analysis_json)
    try:
        q = first_question(analysis)
    except AIError as exc:
        raise HTTPException(502, str(exc))
    interview = Interview(assessment_id=assessment.id, current_question=q.question, current_skill=q.skill, question_number=1, transcript_json="[]")
    db.add(interview); db.commit(); db.refresh(interview)
    return {"id": interview.id, "question_number": 1, "question": q.question, "skill": q.skill, "why": q.why}

@app.get("/api/interviews/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if not interview: raise HTTPException(404, "Interview not found")
    return {"id": interview.id, "status": interview.status, "question": interview.current_question, "skill": interview.current_skill, "question_number": interview.question_number, "report": json.loads(interview.report_json) if interview.report_json else None}

@app.post("/api/interviews/{interview_id}/answer")
def answer(interview_id: int, payload: AnswerRequest, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if not interview: raise HTTPException(404, "Interview not found")
    if interview.status != "active": raise HTTPException(400, "Interview is already complete")
    assessment = db.get(Assessment, interview.assessment_id)
    from .schemas import Analysis
    analysis = Analysis.model_validate_json(assessment.analysis_json)
    transcript = json.loads(interview.transcript_json or "[]")
    old_question, old_skill = interview.current_question, interview.current_skill
    try:
        evaluation = evaluate_turn(analysis, transcript, old_question, old_skill, payload.answer)
        turn = {"question": old_question, "skill": old_skill, "answer": payload.answer, "evaluation": evaluation.model_dump()}
        transcript.append(turn)
        q = next_question(analysis, transcript, evaluation)
    except AIError as exc:
        raise HTTPException(502, str(exc))
    completed = q is None
    if completed:
        try:
            report = final_report(analysis, transcript)
        except AIError as exc:
            raise HTTPException(502, str(exc))
        interview.report_json = report.model_dump_json()
        interview.status = "completed"
        interview.transcript_json = json.dumps(transcript)
        db.commit()
        return {"completed": True, "evaluation": evaluation.model_dump(), "report": report.model_dump()}
    interview.current_question = q.question
    interview.current_skill = q.skill
    interview.question_number += 1
    interview.transcript_json = json.dumps(transcript)
    db.commit()
    return {"completed": False, "evaluation": evaluation.model_dump(), "next_question": q.model_dump(), "question_number": interview.question_number}
