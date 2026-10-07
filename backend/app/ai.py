import json
from google import genai
from google.genai import types
from .config import settings
from .schemas import Analysis, Evaluation, Question, FinalReport

if not settings.gemini_api_key:
    client = None
else:
    client = genai.Client(api_key=settings.gemini_api_key)

class AIError(RuntimeError):
    pass

def _json_call(prompt: str, schema_model):
    if client is None:
        raise AIError("GEMINI_API_KEY is not configured")
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=schema_model.model_json_schema(),
            ),
        )
        return schema_model.model_validate_json(response.text)
    except Exception as exc:
        raise AIError(f"Gemini request failed: {exc}") from exc

def analyze_candidate(jd: str, resume: str) -> Analysis:
    prompt = f"""
You are an evidence-based technical recruiting analyst.
Analyze the job description and resume below.
Do NOT decide whether the person is a good hire yet.
Extract verifiable hiring requirements, resume claims, evidence already present, and evidence gaps.
A keyword alone is weak evidence. Distinguish claimed experience from demonstrated experience.
Use only job-relevant technical/professional information. Ignore protected characteristics and unrelated personal data.
Keep the interview plan to 5-8 high-signal questions.

JOB DESCRIPTION:
{jd[:30000]}

RESUME:
{resume[:30000]}
"""
    return _json_call(prompt, Analysis)

def first_question(analysis: Analysis) -> Question:
    skill = analysis.interview_plan[0] if analysis.interview_plan else (analysis.requirements[0].skill if analysis.requirements else "Technical depth")
    prompt = f"""
Create the first adaptive technical interview question for this candidate.
The purpose is to test actual ownership and depth, not trivia.
Ask for a concrete project, decision, tradeoff, implementation detail, or debugging experience.
Return one question only.

ROLE: {analysis.role_title}
SKILLS/PLAN: {json.dumps(analysis.interview_plan)}
CLAIMS: {json.dumps([c.model_dump() for c in analysis.claims])}
TARGET SKILL: {skill}
"""
    return _json_call(prompt, Question)

def evaluate_turn(analysis: Analysis, transcript: list[dict], question: str, skill: str, answer: str) -> Evaluation:
    prompt = f"""
Evaluate one technical interview answer as an evidence assessor.
Score demonstrated evidence, not eloquence. Do not infer facts that the candidate did not provide.
A strong answer includes concrete ownership, implementation detail, reasoning, tradeoffs, constraints, and outcomes.
If the answer is vague, score lower and identify what remains unverified.

ROLE: {analysis.role_title}
TARGET SKILL: {skill}
QUESTION: {question}
ANSWER: {answer}
PRIOR TRANSCRIPT: {json.dumps(transcript[-4:])}

Return a 0-10 score, confidence 0-1, concise evidence, concern, and whether a follow-up is needed.
"""
    return _json_call(prompt, Evaluation)

def next_question(analysis: Analysis, transcript: list[dict], evaluation: Evaluation) -> Question | None:
    if len(transcript) >= 6:
        return None
    prompt = f"""
Generate the next adaptive technical interview question.
Use the prior answer/evaluation to probe the highest-value uncertainty.
Do not repeat a question. Prefer concrete project evidence and ownership over theoretical trivia.
If a skill is already strongly demonstrated, move to another important requirement.

REQUIREMENTS: {json.dumps([r.model_dump() for r in analysis.requirements])}
CLAIMS: {json.dumps([c.model_dump() for c in analysis.claims])}
TRANSCRIPT: {json.dumps(transcript[-6:])}
LAST EVALUATION: {evaluation.model_dump_json()}
"""
    return _json_call(prompt, Question)

def final_report(analysis: Analysis, transcript: list[dict]) -> FinalReport:
    prompt = f"""
Create an evidence-based technical hiring report.
Separate what the resume claims from what the interview actually demonstrates.
Do not invent employment verification or outcomes.
Do not use protected characteristics or unrelated personal information.
Recommendation must be one of: Strong yes, Yes, Mixed / needs review, No.
Weight high-importance job requirements more heavily.
Use interview evidence and confidence; acknowledge uncertainty.

ROLE: {analysis.role_title}
REQUIREMENTS: {json.dumps([r.model_dump() for r in analysis.requirements])}
RESUME CLAIMS: {json.dumps([c.model_dump() for c in analysis.claims])}
TRANSCRIPT: {json.dumps(transcript)}
"""
    return _json_call(prompt, FinalReport)
