from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from database import get_db
from models import Student, Teacher, CounselLog
from routers.auth import role_required, get_current_user, assert_homeroom_or_admin
from security import encrypt_text, decrypt_text

router = APIRouter()

class CounselCreate(BaseModel):
    student_id: int
    date: date
    channel: Optional[str] = None
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
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

@router.post("", response_model=CounselRead, dependencies=[Depends(role_required("teacher","admin"))])
def create_counsel(payload: CounselCreate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if payload.teacher_id is None and current.role == "teacher":
        payload.teacher_id = current.teacher_id
    rec = CounselLog(
        student_id=payload.student_id,
        teacher_id=payload.teacher_id,
        date=payload.date,
        channel=payload.channel,
        title=payload.title,
        content=encrypt_text(payload.content),
        summary=encrypt_text(payload.summary),
    )
    db.add(rec); db.commit(); db.refresh(rec)
    rec.content = decrypt_text(rec.content); rec.summary = decrypt_text(rec.summary)
    return rec

@router.get("", response_model=List[CounselRead])
def list_counsels(
    student_id: int = Query(..., description="학생 ID"),
    _=Depends(assert_homeroom_or_admin),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = (db.query(CounselLog)
              .filter(CounselLog.student_id == student_id)
              .order_by(desc(CounselLog.date), desc(CounselLog.id))
              .limit(limit).offset(offset).all())
    for r in rows:
        r.content = decrypt_text(r.content); r.summary = decrypt_text(r.summary)
    return rows

@router.patch("/{counsel_id}", response_model=CounselRead)
def update_counsel(counsel_id: int, payload: CounselUpdate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    rec = db.get(CounselLog, counsel_id)
    if not rec: raise HTTPException(status_code=404, detail="상담일지가 존재하지 않습니다.")
    # 권한: 담임/관리자
    assert_homeroom_or_admin(rec.student_id, current, db)
    data = payload.model_dump(exclude_unset=True)
    if "content" in data: data["content"] = encrypt_text(data["content"])
    if "summary" in data: data["summary"] = encrypt_text(data["summary"])
    for k,v in data.items(): setattr(rec, k, v)
    db.commit(); db.refresh(rec)
    rec.content = decrypt_text(rec.content); rec.summary = decrypt_text(rec.summary)
    return rec
