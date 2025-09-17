# models.py
from sqlalchemy import (
    Integer, String, ForeignKey, UniqueConstraint, Text, DateTime, Date, func, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    grade: Mapped[int] = mapped_column(Integer)
    class_no: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(1))  # 'M'/'F'
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent1_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent2_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    counsels = relationship("CounselLog", back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")

class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    subjects = relationship("Subject", back_populates="default_teacher")

class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    default_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)

    default_teacher = relationship("Teacher", back_populates="subjects")
    enrollments = relationship("Enrollment", back_populates="subject", cascade="all, delete-orphan")

class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    term: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "year", "term", name="uq_enroll_unique"),)

    student = relationship("Student", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")
    teacher = relationship("Teacher")

class CounselLog(Base):
    __tablename__ = "counsel_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    student = relationship("Student", back_populates="counsels")
    teacher = relationship("Teacher")

Index("ix_counsel_student_date", CounselLog.student_id, CounselLog.date.desc())

class Attendance(Base):
    __tablename__ = "attendances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)   # present/late/early_leave/absent/period_absence
    reason: Mapped[str] = mapped_column(String(30), nullable=False, default="NORMAL")
    periods: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("student_id", "date", "type", name="uq_attend_student_date_type"),
        Index("ix_attend_student_ym", "student_id", "date"),
    )
    student = relationship("Student", back_populates="attendances")

# ✅ 중간고사 성적 (BCNF)
class MidtermScore(Base):
    """
    학생-과목-연도-학기 단위의 중간고사 점수
    - 후보키: (student_id, subject_id, year, term)
    - score: 0~100 정수(학교 정책에 맞게 확장 가능)
    - comment: 교사 메모(선택)
    """
    __tablename__ = "midterm_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    term: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "year", "term", name="uq_midterm_unique"),
    )

    # (관계는 선택) 조회 편의를 위해 기본 연결만 둠
    student = relationship("Student")
    subject = relationship("Subject")

# models.py (추가)

class FinalScore(Base):
    """
    학생-과목-연도-학기 단위의 기말고사 점수
    후보키: (student_id, subject_id, year, term)
    """
    __tablename__ = "final_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    term: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    score: Mapped[int] = mapped_column(Integer, nullable=False) # 0~100
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "year", "term", name="uq_final_unique"),
    )

    student = relationship("Student")
    subject = relationship("Subject")

# models.py (추가)

class MockExam(Base):
    """
    모의고사 '한 회차' 정보
    - 후보키: (student_id, year, round, name)
      예: 2025년 6월 모평 -> year=2025, round=6, name='모평' (임의 레이블)
    """
    __tablename__ = "mock_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False)  # 1~12 등 달/회차
    name: Mapped[str | None] = mapped_column(String(30), nullable=True)  # '모평', '학평' 등 라벨
    exam_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "year", "round", "name", name="uq_mock_exam_unique"),
    )

    student = relationship("Student")
    scores = relationship("MockExamSubjectScore", back_populates="exam", cascade="all, delete-orphan")


class MockExamSubjectScore(Base):
    """
    모의고사 과목별 점수
    - 과목코드: KOR, ENG, MATH, HIST, SOC1, SOC2, SCI1, SCI2
      (탐구는 2개까지 자유롭게 입력)
    - 후보키: (exam_id, subject_code)
    """
    __tablename__ = "mock_exam_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("mock_exams.id"), nullable=False, index=True)
    subject_code: Mapped[str] = mapped_column(String(10), nullable=False)  # 위 코드 중 하나
    score: Mapped[int] = mapped_column(Integer, nullable=False)            # 0~100 기준(학교 정책에 맞게 조정 가능)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("exam_id", "subject_code", name="uq_mock_exam_subject_unique"),
    )

    exam = relationship("MockExam", back_populates="scores")
