# routers/counsels.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date

from database import get_db
from models import Student, Teacher, CounselLog

router = APIRouter()

# ---- Pydantic 스키마 ----
class CounselCreate(BaseModel):
    student_id: int
    date: date                                 # YYYY-MM-DD
    channel: Optional[str] = None              # 대면/전화/메신저/기타
    title: Optional[str] = None
    content: str
    teacher_id: Optional[int] = None

class CounselUpdate(BaseModel):
    date: Optional[date] = None
    channel: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    teacher_id: Optional[int] = None

class CounselRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    teacher_id: Optional[int]
    date: date
    channel: Optional[str]
    title: Optional[str]
    content: str
    summary: Optional[str]

# ---- 엔드포인트 ----
@router.post("", response_model=CounselRead)
def create_counsel(payload: CounselCreate, db: Session = Depends(get_db)):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if payload.teacher_id is not None and not db.get(Teacher, payload.teacher_id):
        raise HTTPException(status_code=404, detail="교사가 존재하지 않습니다.")
    rec = CounselLog(**payload.model_dump())
    db.add(rec); db.commit(); db.refresh(rec)
    return rec

@router.get("", response_model=List[CounselRead])
def list_counsels(
    student_id: Optional[int] = Query(default=None, description="특정 학생 필터"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(CounselLog)
    if student_id is not None:
        q = q.filter(CounselLog.student_id == student_id)
    return q.order_by(desc(CounselLog.date), desc(CounselLog.id)).limit(limit).offset(offset).all()

@router.patch("/{counsel_id}", response_model=CounselRead)
def update_counsel(counsel_id: int, payload: CounselUpdate, db: Session = Depends(get_db)):
    rec = db.get(CounselLog, counsel_id)
    if not rec:
        raise HTTPException(status_code=404, detail="상담일지가 존재하지 않습니다.")
    data = payload.model_dump(exclude_unset=True)
    if "teacher_id" in data and data["teacher_id"] is not None:
        if not db.get(Teacher, data["teacher_id"]):
            raise HTTPException(status_code=404, detail="교사가 존재하지 않습니다.")
    for k, v in data.items():
        setattr(rec, k, v)
    db.commit(); db.refresh(rec)
    return rec
