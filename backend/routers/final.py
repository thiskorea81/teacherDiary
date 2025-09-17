# routers/final.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

from database import get_db
from models import Student, Subject, FinalScore

router = APIRouter()

# ---------- Pydantic ----------
class FinalUpsert(BaseModel):
    student_id: int
    subject_id: int
    year: int
    term: int = Field(ge=1, le=2)
    score: int = Field(ge=0, le=100)
    comment: Optional[str] = None

class FinalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    subject_id: int
    year: int
    term: int
    score: int
    comment: Optional[str]

class FinalSummary(BaseModel):
    student_id: int
    year: int
    term: int
    subjects: List[Dict]   # [{subject_id, subject_name, score}]
    total: int
    average: float

# ---------- 엔드포인트 ----------
@router.post("", response_model=FinalRead)
def upsert_final(payload: FinalUpsert, db: Session = Depends(get_db)):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status_code=404, detail="과목이 존재하지 않습니다.")

    rec = (db.query(FinalScore)
             .filter_by(student_id=payload.student_id,
                        subject_id=payload.subject_id,
                        year=payload.year, term=payload.term)
             .first())
    if rec:
        rec.score = payload.score
        rec.comment = payload.comment
    else:
        rec = FinalScore(**payload.model_dump())
        db.add(rec)

    db.commit(); db.refresh(rec)
    return rec

@router.get("", response_model=List[FinalRead])
def list_final(student_id: Optional[int] = None,
               year: Optional[int] = None,
               term: Optional[int] = None,
               db: Session = Depends(get_db)):
    q = db.query(FinalScore)
    if student_id is not None:
        q = q.filter(FinalScore.student_id == student_id)
    if year is not None:
        q = q.filter(FinalScore.year == year)
    if term is not None:
        q = q.filter(FinalScore.term == term)
    return q.order_by(FinalScore.student_id, FinalScore.subject_id).all()

@router.get("/summary", response_model=FinalSummary)
def summary_final(student_id: int, year: int, term: int, db: Session = Depends(get_db)):
    rows = (db.query(FinalScore, Subject.name)
              .join(Subject, Subject.id == FinalScore.subject_id)
              .filter(FinalScore.student_id == student_id,
                      FinalScore.year == year,
                      FinalScore.term == term)
              .all())

    subjects = [{"subject_id": r.FinalScore.subject_id,
                 "subject_name": name,
                 "score": r.FinalScore.score} for r, name in rows]

    total = sum(item["score"] for item in subjects) if subjects else 0
    average = round(total / len(subjects), 2) if subjects else 0.0

    return FinalSummary(student_id=student_id, year=year, term=term,
                        subjects=subjects, total=total, average=average)
