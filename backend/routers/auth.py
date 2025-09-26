# routers/auth.py
from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import Optional, Literal, Callable, List
import csv, io

from database import get_db
from models import User, Teacher, Student
from security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter()

# ==================== 공통 / 인증 헬퍼 ====================
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


# ==================== 스키마 ====================
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=6)
    role: Role = "teacher"
    teacher_id: Optional[int] = None
    student_id: Optional[int] = None


# 본인 정보 등 "엄격 이메일 검증"이 필요한 응답
class PublicUserRead(BaseModel):
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


# 관리자 목록/보관 목록 등: 이메일 검증을 느슨하게(str) 처리
class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str]
    role: Role
    is_active: bool
    teacher_id: Optional[int]
    student_id: Optional[int]
    password_change_required: bool


class AdminArchivedUserRead(AdminUserRead):
    archived_year: Optional[int] = None


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


class BulkArchiveIn(BaseModel):
    user_ids: List[int]
    year: int


class BulkIdsIn(BaseModel):
    user_ids: List[int]


# ==================== 회원가입 / 로그인 / 내정보 ====================
@router.post("/signup", response_model=PublicUserRead)
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
        is_active=False,                  # ✅ 승인 전까지 비활성
        password_change_required=False,   # ✅ 가입자는 비밀번호 즉시 변경 강제 안 함
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


@router.get("/me", response_model=PublicUserRead)
def me(current: User = Depends(get_current_user)):
    return current


# ==================== 비밀번호 변경 / 초기화 ====================
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


@router.post("/admin/reset_password_bulk", dependencies=[Depends(role_required("admin"))])
def admin_reset_password_bulk(payload: BulkIdsIn, db: Session = Depends(get_db)):
    """
    선택 사용자 비번을 통일 초기화: 'a123456789!'
    (관리자/본인 계정 보호는 프론트에서 걸고, 백엔드에선 존재하는 id만 처리)
    """
    target_ids = list(set(payload.user_ids or []))
    if not target_ids:
        return {"updated": [], "password": "a123456789!"}

    users = db.query(User).filter(User.id.in_(target_ids)).all()
    new_pwd_hash = hash_password("a123456789!")
    updated = []
    for u in users:
        u.hashed_password = new_pwd_hash
        u.password_change_required = True
        updated.append(u.username)
    db.commit()
    return {"updated": updated, "password": "a123456789!"}


# ==================== 관리자: CSV 업로드 (간단형) ====================
"""
간단 CSV 예시 (헤더 포함):
username,password,full_name,role
t01,Temp!234,김교사,teacher
s1001,Std!234,홍학생,student

- email은 username+"@local" 자동 설정 (관리자 목록 응답은 느슨 검증이라 OK)
- 교사 username이 't'로 시작하면 Teacher 레코드 자동 생성(없으면)
- 학생 username이 's'로 시작하면 student_id를 username에서 s 제거 후 숫자 변환해 자동 매핑(해당 Student가 없으면 생략)
"""
@router.post("/admin/bulk_users_simple", dependencies=[Depends(role_required("admin"))])
def admin_bulk_users_simple(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일을 업로드하세요.")

    content = file.file.read().decode("utf-8-sig")  # BOM 대응
    reader = csv.DictReader(io.StringIO(content))

    created: List[str] = []
    updated: List[str] = []
    skipped: List[str] = []
    skipped_reasons: dict[str, str] = {}

    for row in reader:
        username = (row.get("username") or "").strip()
        password = (row.get("password") or "").strip()
        full_name = (row.get("full_name") or "").strip() or None
        role = (row.get("role") or "").strip().lower()

        if not username or not password or role not in ("teacher", "student", "admin"):
            key = username or "?"
            skipped.append(key)
            skipped_reasons[key] = "필수값 누락 또는 잘못된 role"
            continue

        # email 자동
        email = f"{username}@local"

        # teacher/student 연결 자동 추론
        teacher_id: Optional[int] = None
        student_id: Optional[int] = None

        # 교사: username 이 t* 인 경우 Teacher 자동 생성/매핑
        if username.startswith("t") and role == "teacher":
            teacher = db.query(Teacher).filter(Teacher.name == (full_name or username)).first()
            if not teacher:
                teacher = Teacher(name=(full_name or username))
                db.add(teacher)
                db.flush()  # id 확보
            teacher_id = teacher.id

        # 학생: username 이 s* 인 경우 student_id 자동 추출 (s 접두어 제거 숫자)
        if username.startswith("s") and role == "student":
            try:
                sid_num = int(username[1:])
                stu = db.query(Student).filter(Student.id == sid_num).first()
                # 업로드 데이터 정책에 따라: Student 테이블에 해당 id가 없으면 그냥 연결 생략
                if stu:
                    student_id = stu.id
            except ValueError:
                pass

        # username 또는 email 충돌 시 업데이트
        user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
        if user:
            user.hashed_password = hash_password(password)
            user.full_name = full_name
            user.role = role
            user.teacher_id = teacher_id
            user.student_id = student_id
            user.is_active = True
            user.password_change_required = True
            updated.append(username)
        else:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(password),
                teacher_id=teacher_id,
                student_id=student_id,
                is_active=True,
                password_change_required=True,
            )
            db.add(user)
            created.append(username)

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "skipped_reasons": skipped_reasons,
    }


@router.get("/admin/csv_template", dependencies=[Depends(role_required("admin"))])
def admin_csv_template(kind: str = Query("simple", pattern="^(simple)$")):
    """
    kind=simple -> username,password,full_name,role
    """
    if kind == "simple":
        csv_text = (
            "username,password,full_name,role\n"
            "t01,Temp!234,김교사,teacher\n"
            "s1001,Std!234,홍학생,student\n"
        )
        return Response(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="bulk_users_simple.csv"'},
        )
    raise HTTPException(status_code=400, detail="지원하지 않는 템플릿")


# ==================== 관리자: 승인/목록 ====================
@router.get("/admin/pending", response_model=list[AdminUserRead], dependencies=[Depends(role_required("admin"))])
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


@router.get("/admin/active", response_model=list[AdminUserRead], dependencies=[Depends(role_required("admin"))])
def admin_active(db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_active == True, getattr(User, "archived_year", None) == None).all()


# ==================== 관리자: 보관/삭제 ====================
# 주의: 아래 API들은 users 테이블에 archived_year 컬럼이 있다고 가정합니다.
# (없다면 main.py 스타트업에서 ALTER TABLE 로 추가하세요)
@router.get("/admin/users/archived", response_model=list[AdminArchivedUserRead], dependencies=[Depends(role_required("admin"))])
def admin_archived(db: Session = Depends(get_db)):
    if not hasattr(User, "archived_year"):
        # 컬럼이 없다면 빈 배열 반환(또는 501 에러)
        return []
    return db.query(User).filter(User.archived_year.isnot(None)).all()


@router.post("/admin/users/archive", dependencies=[Depends(role_required("admin"))])
def admin_archive(payload: BulkArchiveIn, db: Session = Depends(get_db)):
    if not hasattr(User, "archived_year"):
        raise HTTPException(status_code=500, detail="archived_year 컬럼이 없습니다. DB 마이그레이션 필요")
    if not payload.user_ids:
        return {"ok": True, "count": 0}
    q = db.query(User).filter(User.id.in_(payload.user_ids))
    count = 0
    for u in q.all():
        u.archived_year = payload.year
        u.is_active = False  # 보관 시 비활성화
        count += 1
    db.commit()
    return {"ok": True, "count": count}


@router.post("/admin/users/unarchive", dependencies=[Depends(role_required("admin"))])
def admin_unarchive(payload: BulkIdsIn, db: Session = Depends(get_db)):
    if not hasattr(User, "archived_year"):
        raise HTTPException(status_code=500, detail="archived_year 컬럼이 없습니다. DB 마이그레이션 필요")
    if not payload.user_ids:
        return {"ok": True, "count": 0}
    q = db.query(User).filter(User.id.in_(payload.user_ids))
    count = 0
    for u in q.all():
        u.archived_year = None
        # 재활성 여부는 정책에 따라. 여기선 활성화로 복원
        u.is_active = True
        count += 1
    db.commit()
    return {"ok": True, "count": count}


@router.post("/admin/users/delete", dependencies=[Depends(role_required("admin"))])
def admin_delete(payload: BulkIdsIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.user_ids:
        return {"ok": True, "count": 0}
    ids = set(payload.user_ids)
    # 자기 자신/다른 관리자 보호 로직(정책에 따라 조정 가능)
    survivors = db.query(User).filter(User.id.in_(ids)).all()
    count = 0
    for u in survivors:
        if u.id == current.id:
            continue
        # 관리자는 삭제 금지(원하면 허용으로 바꾸세요)
        if u.role == "admin":
            continue
        db.delete(u)
        count += 1
    db.commit()
    return {"ok": True, "count": count}


# ==================== 관리자: DB 전체 삭제 (초치명) ====================
class WipeAllIn(BaseModel):
    confirm: str = Field(pattern="^WIPE-ALL$")


@router.post("/admin/db/wipe_all", dependencies=[Depends(role_required("admin"))])
def admin_db_wipe_all(payload: WipeAllIn, db: Session = Depends(get_db)):
    # SQLAlchemy로 전 테이블 드롭/재생성은 보통 앱 기동부에서 수행.
    # 여기서는 SQLite용 간단 초기화 예시(주의: 실제 운영 DB에서는 절대 이렇게 하지 마세요!)
    if payload.confirm != "WIPE-ALL":
        raise HTTPException(status_code=400, detail="확인 문자열이 일치하지 않습니다.")
    # SQLite 전용: 전체 스키마 드롭 후 재생성
    # 안전을 위해 pragma foreign_keys off/on
    db.execute(text("PRAGMA foreign_keys=OFF;"))
    # User-defined 테이블 삭제
    tables = [
        "mock_exam_scores", "mock_exams",
        "final_scores", "midterm_scores",
        "attendances", "counsel_logs",
        "enrollments", "subjects", "teachers",
        "user_settings", "homeroom_assignments",
        "students", "users",
    ]
    for t in tables:
        try:
            db.execute(text(f'DROP TABLE IF EXISTS "{t}";'))
        except Exception:
            pass
    db.execute(text("PRAGMA foreign_keys=ON;"))
    db.commit()
    return {"ok": True, "msg": "DB 스키마 삭제 완료. 앱 재기동 시 create_all 로 재생성됩니다."}


# ==================== 다른 라우터에서 쓰는 권한 헬퍼 ====================
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
