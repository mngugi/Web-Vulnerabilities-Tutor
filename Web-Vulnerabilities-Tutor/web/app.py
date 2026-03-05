from fastapi import FastAPI
from pydantic import BaseModel
from ai_agent.tutor_agent import tutor

app = FastAPI(title="Web Vulnerabilities Tutor")

class TutorRequest(BaseModel):
    vulnerability: str


@app.get("/")
def home():
    return {"message": "Web Vulnerabilities Tutor API running"}


@app.post("/tutor/explain")
def explain_vulnerability(req: TutorRequest):
    return tutor.explain(req.vulnerability)


@app.post("/tutor/defence")
def defence_vulnerability(req: TutorRequest):
    return tutor.defence(req.vulnerability)


@app.post("/tutor/quiz")
def quiz_vulnerability(req: TutorRequest):
    return tutor.quiz(req.vulnerability)