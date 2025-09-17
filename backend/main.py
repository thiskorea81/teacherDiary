# main.py
# 실행: uvicorn main:app --reload

from fastapi import FastAPI
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Teacher
from routers.core import router as core_router
from routers.midterm import router as midterm_router
from routers.counsels import router as counsels_router
from routers.attendance import router as attendance_router
from routers.final import router as final_router
from routers.mock_exam import router as mock_router

app = FastAPI(title="담임 상담 프로그램 (파일 분리 2차: 상담/출결)")

# --- DB 테이블 생성 & placeholder 교사 보장 ---
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        _ensure_placeholder_teacher(db)

def _ensure_placeholder_teacher(db: Session):
    if not db.query(Teacher).filter(Teacher.name == "교사").first():
        db.add(Teacher(name="교사")); db.commit()

# --- 라우터 장착 ---
app.include_router(core_router,      prefix="/core",            tags=["core"])
app.include_router(counsels_router,  prefix="/counsels",        tags=["counsels"])
app.include_router(attendance_router,prefix="/attendance",      tags=["attendance"])
app.include_router(midterm_router,   prefix="/grades/midterm",  tags=["grades: midterm"])
app.include_router(final_router, prefix="/grades/final", tags=["grades: final"])
app.include_router(mock_router, prefix="/grades/mock", tags=["grades: mock"])