from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from database import get_db
from models import Student, Teacher, Subject, Enrollment
from routers.auth import role_required, get_current_user, assert_can_view_student

router = APIRouter()

class StudentCreate(BaseModel):
    student_no: str; name: str; grade: int; class_no: int; number: int
    gender: str = Field(pattern="^[MF]$")
    phone: Optional[str] = None; parent1_phone: Optional[str] = None
    parent2_phone: Optional[str] = None; address: Optional[str] = None
    homeroom_teacher_id: Optional[int] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = None; grade: Optional[int] = None
    class_no: Optional[int] = None; number: Optional[int] = None
    gender: Optional[str] = Field(default=None, pattern="^[MF]$")
    phone: Optional[str] = None; parent1_phone: Optional[str] = None
    parent2_phone: Optional[str] = None; address: Optional[str] = None
    homeroom_teacher_id: Optional[int] = None

class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; student_no: str; name: str; grade: int; class_no: int; number: int
    gender: str; phone: Optional[str]; parent1_phone: Optional[str]
    parent2_phone: Optional[str]; address: Optional[str]
    homeroom_teacher_id: Optional[int]

class TeacherCreate(BaseModel):
    name: str

class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str

class SubjectCreate(BaseModel):
    name: str; default_teacher_id: Optional[int] = None

class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; default_teacher_id: Optional[int]

class EnrollmentCreate(BaseModel):
    student_id: int; subject_id: int; year: int
    term: int = Field(ge=1, le=2); teacher_id: Optional[int] = None

class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; student_id: int; subject_id: int; year: int; term: int; teacher_id: Optional[int]

def _get_placeholder_teacher_id(db: Session) -> int:
    t = db.query(Teacher).filter(Teacher.name == "교사").first()
    if not t:
        t = Teacher(name="교사"); db.add(t); db.commit(); db.refresh(t)
    return t.id

@router.post("/students", response_model=StudentRead, dependencies=[Depends(role_required("teacher","admin"))])
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    if db.query(Student).filter_by(student_no=payload.student_no).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 학번입니다.")
    s = Student(**payload.model_dump())
    db.add(s); db.commit(); db.refresh(s); return s

@router.get("/students", response_model=List[StudentRead],
            dependencies=[Depends(role_required("teacher","admin"))])
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).order_by(Student.grade, Student.class_no, Student.number).all()

@router.get("/students/{student_id}", response_model=StudentRead)
def get_student(student_id: int, _=Depends(assert_can_view_student), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s: raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    return s

@router.get("/students/me", response_model=StudentRead)
def get_student_me(current = Depends(get_current_user), db: Session = Depends(get_db)):
    if current.role != "student" or not current.student_id:
        raise HTTPException(status_code=403, detail="학생 계정만 접근할 수 있습니다.")
    s = db.get(Student, current.student_id)
    if not s: raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    return s

@router.patch("/students/{student_id}", response_model=StudentRead,
              dependencies=[Depends(role_required("teacher","admin"))])
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s: raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(s, k, v)
    db.commit(); db.refresh(s); return s

@router.post("/teachers", response_model=TeacherRead, dependencies=[Depends(role_required("teacher","admin"))])
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    if db.query(Teacher).filter_by(name=payload.name).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 교사 이름입니다.")
    t = Teacher(**payload.model_dump()); db.add(t); db.commit(); db.refresh(t); return t

@router.get("/teachers", response_model=List[TeacherRead], dependencies=[Depends(role_required("teacher","admin"))])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).order_by(Teacher.name).all()

@router.post("/subjects", response_model=SubjectRead, dependencies=[Depends(role_required("teacher","admin"))])
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    if db.query(Subject).filter_by(name=payload.name).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 과목명입니다.")
    sub = Subject(**payload.model_dump()); db.add(sub); db.commit(); db.refresh(sub); return sub

@router.get("/subjects", response_model=List[SubjectRead], dependencies=[Depends(role_required("teacher","admin"))])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.name).all()

@router.post("/enrollments", response_model=EnrollmentRead, dependencies=[Depends(role_required("teacher","admin"))])
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)):
    if not db.get(Student, payload.student_id): raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if not db.get(Subject, payload.subject_id): raise HTTPException(status_code=404, detail="과목이 존재하지 않습니다.")
    teacher_id = payload.teacher_id or _get_placeholder_teacher_id(db)
    dup = (db.query(Enrollment)
           .filter_by(student_id=payload.student_id, subject_id=payload.subject_id,
                      year=payload.year, term=payload.term).first())
    if dup: raise HTTPException(status_code=400, detail="이미 동일한 (학생, 과목, 연도, 학기) 수강이 존재합니다.")
    e = Enrollment(student_id=payload.student_id, subject_id=payload.subject_id,
                   year=payload.year, term=payload.term, teacher_id=teacher_id)
    db.add(e); db.commit(); db.refresh(e); return e
