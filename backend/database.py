# database.py
# SQLite 연결/세션 및 Declarative Base 정의

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 로컬 SQLite 파일(DB 파일명은 필요 시 변경)
SQLALCHEMY_DATABASE_URL = "sqlite:///./school.db"

# check_same_thread=False: SQLite에서 단일 스레드 제약 완화(FastAPI 개발환경 편의)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: 모델들이 상속할 Declarative Base
Base = declarative_base()

# 의존성 주입용 세션 생성기
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
