# routers/mock_exam.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date

from database import get_db
from models import Student, MockExam, MockExamSubjectScore

router = APIRouter()

VALID_SUBJECTS = {"KOR","ENG","MATH","HIST","SOC1","SOC2","SCI1","SCI2"}

# ---------- Pydantic ----------
class ExamCreate(BaseModel):
    student_id: int
    year: int
    round: int = Field(ge=1, le=12, description="보통 월/회차(1~12)")
    name: Optional[str] = Field(default="모의고사", description="예: '모평', '학평'")
    exam_date: Optional[date] = None

class ExamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    year: int
    round: int
    name: Optional[str]
    exam_date: Optional[date]

class ScoreUpsert(BaseModel):
    exam_id: int
    subject_code: str = Field(description="KOR/ENG/MATH/HIST/SOC1/SOC2/SCI1/SCI2")
    score: int = Field(ge=0, le=100)
    comment: Optional[str] = None

class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int
    subject_code: str
    score: int
    comment: Optional[str]

class ExamWithScores(BaseModel):
    exam: ExamRead
    scores: List[ScoreRead]

class ExamSummary(BaseModel):
    exam: ExamRead
    scores: Dict[str, int]     # {"KOR": 92, "ENG": 88, ...}
    total: int
    average: float

# ---------- 엔드포인트 ----------
@router.post("/exams", response_model=ExamRead)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    # 동일 회차 중복 방지 (학생,연도,회차,이름)
    exists = (db.query(MockExam)
                .filter_by(student_id=payload.student_id, year=payload.year,
                           round=payload.round, name=payload.name)
                .first())
    if exists:
        return exists
    rec = MockExam(**payload.model_dump())
    db.add(rec); db.commit(); db.refresh(rec)
    return rec

@router.get("/exams", response_model=List[ExamRead])
def list_exams(student_id: Optional[int] = None,
               year: Optional[int] = None,
               db: Session = Depends(get_db)):
    q = db.query(MockExam)
    if student_id is not None:
        q = q.filter(MockExam.student_id == student_id)
    if year is not None:
        q = q.filter(MockExam.year == year)
    return q.order_by(MockExam.student_id, MockExam.year, MockExam.round).all()

@router.post("/scores", response_model=ScoreRead)
def upsert_score(payload: ScoreUpsert, db: Session = Depends(get_db)):
    if payload.subject_code not in VALID_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"subject_code는 {sorted(VALID_SUBJECTS)} 중 하나여야 합니다.")
    exam = db.get(MockExam, payload.exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="모의고사 회차가 존재하지 않습니다.")

    rec = (db.query(MockExamSubjectScore)
             .filter_by(exam_id=payload.exam_id, subject_code=payload.subject_code)
             .first())
    if rec:
        rec.score = payload.score
        rec.comment = payload.comment
    else:
        rec = MockExamSubjectScore(**payload.model_dump())
        db.add(rec)
    db.commit(); db.refresh(rec)
    return rec

@router.get("/scores", response_model=List[ScoreRead])
def list_scores(exam_id: int, db: Session = Depends(get_db)):
    return (db.query(MockExamSubjectScore)
              .filter(MockExamSubjectScore.exam_id == exam_id)
              .order_by(MockExamSubjectScore.subject_code).all())

@router.get("/exams/{exam_id}", response_model=ExamWithScores)
def get_exam_with_scores(exam_id: int, db: Session = Depends(get_db)):
    exam = db.get(MockExam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="모의고사 회차가 존재하지 않습니다.")
    scores = (db.query(MockExamSubjectScore)
                .filter(MockExamSubjectScore.exam_id == exam_id)
                .order_by(MockExamSubjectScore.subject_code).all())
    return ExamWithScores(exam=exam, scores=scores)

@router.get("/summary/{exam_id}", response_model=ExamSummary)
def exam_summary(exam_id: int, db: Session = Depends(get_db)):
    exam = db.get(MockExam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="모의고사 회차가 존재하지 않습니다.")
    rows = (db.query(MockExamSubjectScore)
              .filter(MockExamSubjectScore.exam_id == exam_id)
              .all())
    scores_map = {r.subject_code: r.score for r in rows}
    total = sum(scores_map.values()) if scores_map else 0
    avg = round(total / len(scores_map), 2) if scores_map else 0.0
    return ExamSummary(exam=exam, scores=scores_map, total=total, average=avg)
