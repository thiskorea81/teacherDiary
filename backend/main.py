# main.py
# - 서버 실행: uvicorn main:app --reload
import uvicorn

from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from models import Base, Teacher, User
from security import hash_password
from database import Base, engine, SessionLocal
from security import hash_password
from models import Teacher
from routers.auth import router as auth_router
from routers.core import router as core_router
from routers.counsels import router as counsels_router
from routers.attendance import router as attendance_router
from routers.midterm import router as midterm_router
from routers.final import router as final_router
from routers.mock_exam import router as mock_router
from routers.settings import router as settings_router
# main.py (상단)
from fastapi.middleware.cors import CORSMiddleware
from routers.homeroom_upload import router as homeroom_upload_router 

def _ensure_users_add_pwdreq_column(db: Session):
    insp = inspect(db.bind)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "password_change_required" not in cols:
        db.execute(text(
            "ALTER TABLE users ADD COLUMN password_change_required BOOLEAN NOT NULL DEFAULT 1"
        ))
        db.commit()

def _ensure_placeholder_teacher(db: Session):
    if not db.query(Teacher).filter(Teacher.name == "교사").first():
        db.add(Teacher(name="교사")); db.commit()

def _ensure_admin_user(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        db.add(User(
            username="admin",
            email="admin@example.com",
            full_name="Administrator",
            hashed_password=hash_password("admin"),
            role="admin",
            is_active=True,
            password_change_required=True,
        ))
        db.commit()

def _ensure_students_add_birthdate(db: Session):
    insp = inspect(db.bind)
    cols = [c["name"] for c in insp.get_columns("students")]
    if "birthdate" not in cols:
        db.execute(text("ALTER TABLE students ADD COLUMN birthdate DATE"))
        db.commit()

# --- 보관 연도 컬럼 보강: users.archived_year 없으면 추가 ---
def _ensure_users_add_archived_year(db: Session):
    insp = inspect(db.bind)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "archived_year" not in cols:
        db.execute(text("ALTER TABLE users ADD COLUMN archived_year INTEGER"))
        db.commit()
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _ensure_users_add_pwdreq_column(db)
        _ensure_users_add_archived_year(db)         # (이미 있으시면 유지)
        _ensure_students_add_birthdate(db)          # ✅ 새로 추가
        _ensure_placeholder_teacher(db)
        _ensure_admin_user(db)
    finally:
        db.close()
    yield
    # shutdown 시 할 일 있으면 여기에…


app = FastAPI(title="담임 상담 프로그램 (FastAPI)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # OPTIONS 포함
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router,       prefix="/auth",          tags=["auth"])
app.include_router(core_router,       prefix="/core",          tags=["core"])
app.include_router(counsels_router,   prefix="/counsels",      tags=["counsels"])
app.include_router(attendance_router, prefix="/attendance",    tags=["attendance"])
app.include_router(midterm_router,    prefix="/grades/midterm",tags=["grades: midterm"])
app.include_router(final_router,      prefix="/grades/final",  tags=["grades: final"])
app.include_router(mock_router,       prefix="/grades/mock",   tags=["grades: mock"])
app.include_router(settings_router,   prefix="/settings",      tags=["settings"])
app.include_router(homeroom_upload_router, prefix="", tags=["homeroom"])

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)