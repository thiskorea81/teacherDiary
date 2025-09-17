# routers/midterm.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

from database import get_db
from models import Student, Subject, MidtermScore

router = APIRouter()

# ---------- Pydantic 스키마 ----------
class MidtermUpsert(BaseModel):
    student_id: int
    subject_id: int
    year: int
    term: int = Field(ge=1, le=2)
    score: int = Field(ge=0, le=100)
    comment: Optional[str] = None

class MidtermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    subject_id: int
    year: int
    term: int
    score: int
    comment: Optional[str]

class MidtermSummary(BaseModel):
    student_id: int
    year: int
    term: int
    subjects: List[Dict]   # [{subject_id, subject_name, score}]
    total: int
    average: float

# ---------- 엔드포인트 ----------
@router.post("", response_model=MidtermRead)
def upsert_midterm(payload: MidtermUpsert, db: Session = Depends(get_db)):
    # 존재성 검사
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status_code=404, detail="과목이 존재하지 않습니다.")

    rec = (db.query(MidtermScore)
             .filter_by(student_id=payload.student_id,
                        subject_id=payload.subject_id,
                        year=payload.year, term=payload.term)
             .first())
    if rec:
        rec.score = payload.score
        rec.comment = payload.comment
    else:
        rec = MidtermScore(**payload.model_dump())
        db.add(rec)

    db.commit(); db.refresh(rec)
    return rec

@router.get("", response_model=List[MidtermRead])
def list_midterm(student_id: Optional[int] = None,
                 year: Optional[int] = None,
                 term: Optional[int] = None,
                 db: Session = Depends(get_db)):
    q = db.query(MidtermScore)
    if student_id is not None: q = q.filter(MidtermScore.student_id == student_id)
    if year is not None: q = q.filter(MidtermScore.year == year)
    if term is not None: q = q.filter(MidtermScore.term == term)
    return q.order_by(MidtermScore.student_id, MidtermScore.subject_id).all()

@router.get("/summary", response_model=MidtermSummary)
def summary_midterm(student_id: int, year: int, term: int, db: Session = Depends(get_db)):
    rows = (db.query(MidtermScore, Subject.name)
              .join(Subject, Subject.id == MidtermScore.subject_id)
              .filter(MidtermScore.student_id == student_id,
                      MidtermScore.year == year,
                      MidtermScore.term == term)
              .all())

    subjects = [{"subject_id": r.MidtermScore.subject_id,
                 "subject_name": name,
                 "score": r.MidtermScore.score} for r, name in rows]

    total = sum(item["score"] for item in subjects) if subjects else 0
    average = round(total / len(subjects), 2) if subjects else 0.0

    return MidtermSummary(student_id=student_id, year=year, term=term,
                          subjects=subjects, total=total, average=average)
