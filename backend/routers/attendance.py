# routers/attendance.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date

from database import get_db
from models import Student, Attendance

router = APIRouter()

# ---- 상수 ----
VALID_TYPES = {"present", "late", "early_leave", "absent", "period_absence"}
VALID_REASONS = {"NORMAL", "EXTERNAL_DOMESTIC", "EXTERNAL_OVERSEAS", "MENSTRUAL", "OFFICIAL"}

# ---- Pydantic 스키마 ----
class AttendanceCreate(BaseModel):
    student_id: int
    date: date
    type: str = Field(description="present/late/early_leave/absent/period_absence")
    reason: str = Field(default="NORMAL", description="NORMAL/EXTERNAL_DOMESTIC/EXTERNAL_OVERSEAS/MENSTRUAL/OFFICIAL")
    periods: int = Field(default=0, ge=0, description="결과 교시 수 (period_absence일 때 권장)")
    note: Optional[str] = None

class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    date: date
    type: str
    reason: str
    periods: int
    note: Optional[str]

class AttendanceSummary(BaseModel):
    student_id: int
    year: int
    counts_by_type: Dict[str, int]
    external_domestic_days: int
    external_overseas_days: int
    menstrual_months_used: List[str]
    warnings: List[str]

# ---- 유틸 ----
def _yyyymm(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"

# ---- 엔드포인트 ----
@router.post("", response_model=AttendanceRead)
def create_attendance(payload: AttendanceCreate, db: Session = Depends(get_db)):
    if payload.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"type은 {sorted(VALID_TYPES)} 중 하나여야 합니다.")
    if payload.reason not in VALID_REASONS:
        raise HTTPException(status_code=400, detail=f"reason은 {sorted(VALID_REASONS)} 중 하나여야 합니다.")
    stu = db.get(Student, payload.student_id)
    if not stu:
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")

    # 1) 생리 사유: 여학생만, 월 1회
    if payload.reason == "MENSTRUAL":
        if stu.gender != "F":
            raise HTTPException(status_code=400, detail="생리 사유는 여학생에게만 허용됩니다.")
        exists = (db.query(Attendance)
                    .filter(Attendance.student_id == payload.student_id,
                            func.extract("year", Attendance.date) == payload.date.year,
                            func.extract("month", Attendance.date) == payload.date.month,
                            Attendance.reason == "MENSTRUAL")
                    .first())
        if exists:
            raise HTTPException(status_code=400, detail="해당 월의 생리 사유 출결은 이미 등록되어 있습니다. (월 1회)")

    # 2) 교외체험 한도(국내7/국외30) — 연간 distinct 날짜 기준
    if payload.reason in {"EXTERNAL_DOMESTIC", "EXTERNAL_OVERSEAS"}:
        base = (db.query(func.count(distinct(Attendance.date)))
                  .filter(Attendance.student_id == payload.student_id,
                          func.extract("year", Attendance.date) == payload.date.year))
        if payload.reason == "EXTERNAL_DOMESTIC":
            used = base.filter(Attendance.reason == "EXTERNAL_DOMESTIC").scalar() or 0
            dup_day = (db.query(Attendance.id)
                        .filter(Attendance.student_id == payload.student_id,
                                Attendance.date == payload.date,
                                Attendance.reason == "EXTERNAL_DOMESTIC")
                        .first())
            if not dup_day and used >= 7:
                raise HTTPException(status_code=400, detail="교외체험(국내) 연간 7일 한도를 초과합니다.")
        else:
            used = base.filter(Attendance.reason == "EXTERNAL_OVERSEAS").scalar() or 0
            dup_day = (db.query(Attendance.id)
                        .filter(Attendance.student_id == payload.student_id,
                                Attendance.date == payload.date,
                                Attendance.reason == "EXTERNAL_OVERSEAS")
                        .first())
            if not dup_day and used >= 30:
                raise HTTPException(status_code=400, detail="교외체험(국외) 연간 30일 한도를 초과합니다.")

    # 3) (student_id, date, type) 유니크 충돌 방지
    dup = (db.query(Attendance)
            .filter_by(student_id=payload.student_id, date=payload.date, type=payload.type)
            .first())
    if dup:
        raise HTTPException(status_code=400, detail="해당 날짜에 같은 유형(type)의 출결이 이미 존재합니다.")

    rec = Attendance(**payload.model_dump())
    db.add(rec); db.commit(); db.refresh(rec)
    return rec

@router.get("", response_model=List[AttendanceRead])
def list_attendance(
    student_id: int = Query(..., description="학생 ID (필수)"),
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Attendance).where(Attendance.student_id == student_id)
    if start:
        q = q.filter(Attendance.date >= start)
    if end:
        q = q.filter(Attendance.date <= end)
    return q.order_by(Attendance.date.asc(), Attendance.type.asc()).all()

@router.get("/summary", response_model=AttendanceSummary)
def attendance_summary(
    student_id: int,
    year: int,
    db: Session = Depends(get_db),
):
    # 유형별 건수
    counts = {t: 0 for t in VALID_TYPES}
    rows = (db.query(Attendance.type, func.count(Attendance.id))
              .filter(Attendance.student_id == student_id,
                      func.extract("year", Attendance.date) == year)
              .group_by(Attendance.type)
              .all())
    for t, c in rows:
        counts[t] = c

    # 교외체험 날짜 수(연간 distinct)
    ext_dom = (db.query(func.count(distinct(Attendance.date)))
                 .filter(Attendance.student_id == student_id,
                         func.extract("year", Attendance.date) == year,
                         Attendance.reason == "EXTERNAL_DOMESTIC")
                 .scalar()) or 0
    ext_ovr = (db.query(func.count(distinct(Attendance.date)))
                 .filter(Attendance.student_id == student_id,
                         func.extract("year", Attendance.date) == year,
                         Attendance.reason == "EXTERNAL_OVERSEAS")
                 .scalar()) or 0

    # 생리 사유 월(YYYY-MM)
    months = (db.query(Attendance.date)
                .filter(Attendance.student_id == student_id,
                        func.extract("year", Attendance.date) == year,
                        Attendance.reason == "MENSTRUAL")
                .all())
    menstrual_months = sorted({_yyyymm(d[0]) for d in months})

    warnings: List[str] = []
    if ext_dom > 7:
        warnings.append(f"교외체험(국내) {ext_dom}일 사용 — 연간 7일 초과")
    if ext_ovr > 30:
        warnings.append(f"교외체험(국외) {ext_ovr}일 사용 — 연간 30일 초과")
    if len(menstrual_months) != len(set(menstrual_months)):
        warnings.append("특정 월에 생리 사유가 2건 이상 존재합니다. (데이터 점검 필요)")

    return AttendanceSummary(
        student_id=student_id,
        year=year,
        counts_by_type=counts,
        external_domestic_days=ext_dom,
        external_overseas_days=ext_ovr,
        menstrual_months_used=menstrual_months,
        warnings=warnings,
    )
