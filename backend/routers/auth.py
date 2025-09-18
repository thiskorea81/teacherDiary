# routers/auth.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.orm import Session
from typing import Optional, Literal, Callable, List
import csv, io

from database import get_db
from models import User, Teacher, Student
from security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter()

# -------------------- OAuth2 / 공통 --------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
Role = Literal["admin", "teacher", "student"]


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 유효하지 않습니다."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 유효하지 않습니다."
        )
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자 없음 또는 비활성화"
        )
    return user


def role_required(*roles: Role) -> Callable:
    """
    엔드포인트에 역할 제한을 거는 의존성 팩토리
    예) dependencies=[Depends(role_required("admin","teacher"))]
    """
    def _dep(current: User = Depends(get_current_user)):
        if current.role not in roles:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        return True
    return _dep


# -------------------- 스키마 --------------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=6)
    role: Role = "teacher"
    teacher_id: Optional[int] = None
    student_id: Optional[int] = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str]
    role: Role
    is_active: bool
    teacher_id: Optional[int]
    student_id: Optional[int]
    password_change_required: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    password_change_required: bool  # 첫 로그인 시 비밀번호 변경 강제 여부


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class AdminResetPassword(BaseModel):
    user_id: int
    new_password: str = Field(min_length=6)

class ApproveUser(BaseModel):
    user_id: int
    approve: bool = True

# -------------------- 회원가입 / 로그인 / 내정보 --------------------
@router.post("/signup", response_model=UserRead)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    # 1) admin 가입 차단
    if payload.role == "admin":
        raise HTTPException(status_code=400, detail="관리자 계정은 직접 생성할 수 없습니다.")

    # 중복 체크
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자명입니다.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

    # 관계 유효성
    if payload.teacher_id and not db.get(Teacher, payload.teacher_id):
        raise HTTPException(status_code=400, detail="teacher_id가 유효하지 않습니다.")
    if payload.student_id and not db.get(Student, payload.student_id):
        raise HTTPException(status_code=400, detail="student_id가 유효하지 않습니다.")

    # 2) 가입은 비활성 상태로 생성 → 관리자가 승인 시 활성화
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,  # "teacher" | "student"
        teacher_id=payload.teacher_id,
        student_id=payload.student_id,
        is_active=False,                 # ✅ 승인 전까지 비활성
        password_change_required=True,   # 첫 로그인 시 변경
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2PasswordRequestForm: username, password (x-www-form-urlencoded)
    """
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="승인 대기중인 계정입니다. 관리자에게 문의하세요.")

    token = create_access_token(subject=user.username, extra_claims={"role": user.role})
    return TokenResponse(
        access_token=token,
        password_change_required=user.password_change_required,
    )


@router.get("/me", response_model=UserRead)
def me(current: User = Depends(get_current_user)):
    return current


# -------------------- 비밀번호 변경 / 초기화 --------------------
@router.post("/change_password")
def change_password(
    payload: PasswordChange,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    current.hashed_password = hash_password(payload.new_password)
    current.password_change_required = False  # 변경 완료 → 강제 해제
    db.commit()
    return {"ok": True}


@router.post("/admin/reset_password", dependencies=[Depends(role_required("admin"))])
def admin_reset_password(payload: AdminResetPassword, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자가 존재하지 않습니다.")
    user.hashed_password = hash_password(payload.new_password)
    user.password_change_required = True  # 다음 로그인에 변경 강제
    db.commit()
    return {"ok": True}


# -------------------- 관리자: CSV 일괄 업로드 --------------------
"""
CSV 예시 (헤더 포함):
username,email,role,password,full_name,teacher_id,student_id
t01,t01@sch.kr,teacher,Temp!234,김교사,1,
s1001,s1001@sch.kr,student,Std!234,홍학생,,101
"""
@router.post("/admin/bulk_csv", dependencies=[Depends(role_required("admin"))])
def admin_bulk_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일을 업로드하세요.")

    content = file.file.read().decode("utf-8-sig")  # BOM 대응
    reader = csv.DictReader(io.StringIO(content))

    created: List[str] = []
    updated: List[str] = []
    skipped: List[str] = []

    for row in reader:
        username = (row.get("username") or "").strip()
        email = (row.get("email") or "").strip()
        role = (row.get("role") or "teacher").strip()
        password = (row.get("password") or "").strip()
        full_name = (row.get("full_name") or "").strip() or None

        teacher_id = row.get("teacher_id")
        student_id = row.get("student_id")
        teacher_id = int(teacher_id) if teacher_id and str(teacher_id).strip() else None
        student_id = int(student_id) if student_id and str(student_id).strip() else None

        if not username or not email or not password or role not in ("admin", "teacher", "student"):
            skipped.append(username or email or "?")
            continue

        if teacher_id and not db.get(Teacher, teacher_id):
            skipped.append(username)
            continue
        if student_id and not db.get(Student, student_id):
            skipped.append(username)
            continue

        # username 또는 email이 겹치면 업데이트 정책
        user = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if user:
            user.hashed_password = hash_password(password)
            user.role = role
            user.full_name = full_name
            user.teacher_id = teacher_id
            user.student_id = student_id
            user.password_change_required = True  # 다음 로그인 시 변경 강제
            updated.append(username)
        else:
            user = User(
                username=username,
                email=email,
                role=role,
                full_name=full_name,
                hashed_password=hash_password(password),
                teacher_id=teacher_id,
                student_id=student_id,
                is_active=True,
                password_change_required=True,
            )
            db.add(user)
            created.append(username)

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}

# -------------------- 관리자 승인/거부 --------------------
@router.get("/admin/pending", response_model=list[UserRead], dependencies=[Depends(role_required("admin"))])
def admin_pending(db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_active == False).all()

@router.post("/admin/approve", dependencies=[Depends(role_required("admin"))])
def admin_approve(payload: ApproveUser, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자가 존재하지 않습니다.")
    user.is_active = bool(payload.approve)
    db.commit()
    return {"ok": True, "user_id": user.id, "is_active": user.is_active}

@router.get("/admin/active", response_model=list[UserRead], dependencies=[Depends(role_required("admin"))])
def admin_active(db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_active == True).all()

# -------------------- (옵션) 관리자 핑 --------------------
@router.get("/admin/ping", dependencies=[Depends(role_required("admin"))])
def admin_ping():
    return {"ok": True, "msg": "admin only!"}


# -------------------- 다른 라우터에서 쓰는 권한 헬퍼 --------------------
from typing import Optional as _Optional  # 이름 충돌 방지용

def assert_can_view_student(
    student_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    - admin/teacher: 열람 허용
    - student: 본인 student_id만 열람 허용
    """
    if current.role in ("admin", "teacher"):
        return
    if current.role == "student" and current.student_id == student_id:
        return
    raise HTTPException(status_code=403, detail="학생 정보 열람 권한이 없습니다.")


def assert_homeroom_or_admin(
    student_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    상담 열람/수정 권한:
    - 관리자
    - 담임(학생.homeroom_teacher_id == current.teacher_id)
    """
    if current.role == "admin":
        return
    if current.role != "teacher":
        raise HTTPException(status_code=403, detail="담임 교사만 접근할 수 있습니다.")
    stu: _Optional[Student] = db.get(Student, student_id)
    if not stu:
        raise HTTPException(status_code=404, detail="학생이 존재하지 않습니다.")
    if not stu.homeroom_teacher_id or current.teacher_id != stu.homeroom_teacher_id:
        raise HTTPException(status_code=403, detail="담임 교사만 접근할 수 있습니다.")
