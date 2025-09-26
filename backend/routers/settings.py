# routers/settings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import os, requests
from datetime import datetime

from database import get_db
from models import UserSetting
from routers.auth import get_current_user, User
from security import encrypt_secret, decrypt_secret

from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import HomeroomAssignment
from routers.auth import get_current_user, role_required
from models import User

router = APIRouter()

# ---------------- 기본 모델 ----------------
class ApiKeyIn(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai)$", description="AI 제공자")
    api_key: str = Field(min_length=8)

class ApiKeyOut(BaseModel):
    provider: str
    has_key: bool
    masked: str | None = None

def _mask_key(k: str) -> str:
    if not k: return ""
    return f"****{k[-4:]}"

# ---------------- DB 접근 ----------------
def _load_user_ai_key(db: Session, user_id: int, provider: str) -> str:
    setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if not setting:
        raise HTTPException(status_code=400, detail="AI 설정 없음")
    encrypted = None
    if provider == "gemini":
        encrypted = setting.ai_api_key_encrypted
    elif provider == "openai":
        encrypted = setting.openai_api_key_encrypted
    if not encrypted:
        raise HTTPException(status_code=400, detail=f"{provider} API 키가 저장되지 않았습니다.")
    key = decrypt_secret(encrypted)
    if not key:
        raise HTTPException(status_code=400, detail=f"{provider} API 키 복호화 실패")
    return key

# ---------------- CRUD ----------------
@router.get("/me/ai-key/{provider}", response_model=ApiKeyOut)
def get_my_ai_key(provider: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if provider not in ("gemini","openai"):
        raise HTTPException(400,"provider must be gemini or openai")
    setting = db.query(UserSetting).filter(UserSetting.user_id == current.id).first()
    if not setting: return ApiKeyOut(provider=provider, has_key=False)
    enc = setting.ai_api_key_encrypted if provider=="gemini" else setting.openai_api_key_encrypted
    if not enc: return ApiKeyOut(provider=provider, has_key=False)
    plain = decrypt_secret(enc)
    return ApiKeyOut(provider=provider, has_key=True, masked=_mask_key(plain))

@router.post("/me/ai-key", response_model=ApiKeyOut)
def set_my_ai_key(payload: ApiKeyIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    setting = db.query(UserSetting).filter(UserSetting.user_id == current.id).first()
    if not setting:
        setting = UserSetting(user_id=current.id)
        db.add(setting)
    if payload.provider == "gemini":
        setting.ai_api_key_encrypted = encrypt_secret(payload.api_key)
    else:
        setting.openai_api_key_encrypted = encrypt_secret(payload.api_key)
    setting.updated_at = datetime.utcnow()
    db.commit()
    return ApiKeyOut(provider=payload.provider, has_key=True, masked=_mask_key(payload.api_key))

@router.delete("/me/ai-key/{provider}")
def delete_my_ai_key(provider: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if provider not in ("gemini","openai"):
        raise HTTPException(400,"provider must be gemini or openai")
    setting = db.query(UserSetting).filter(UserSetting.user_id == current.id).first()
    if not setting: return {"ok":True}
    if provider=="gemini":
        setting.ai_api_key_encrypted = None
    else:
        setting.openai_api_key_encrypted = None
    setting.updated_at = datetime.utcnow()
    db.commit()
    return {"ok":True}

# ---------------- 테스트 호출 ----------------
class AiTestIn(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai)$")
    prompt: str
    model: str | None = None

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-5-mini",
}

class AiTestOut(BaseModel):
    provider: str
    model: str
    output_text: str

@router.post("/ai/test", response_model=AiTestOut)
def test_ai(payload: AiTestIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = _load_user_ai_key(db, current.id, payload.provider)
    if payload.provider == "gemini":
        model = payload.model or DEFAULT_MODELS["gemini"]
        base = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")
        url = f"{base}/v1beta/models/{model}:generateContent?key={key}"
        body = {"contents":[{"parts":[{"text":payload.prompt}]}]}
        r = requests.post(url, json=body, timeout=20)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Gemini 오류: {r.text}")
        data = r.json()
        text = ""
        try:
            cands = data.get("candidates") or []
            if cands:
                parts = (cands[0].get("content") or {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts)
        except:  # noqa
            text = ""
        return AiTestOut(provider="gemini", model=model, output_text=text or "(빈 응답)")
    else:
        model = payload.model or DEFAULT_MODELS["openai"]
        url = "https://api.openai.com/v1/chat/completions"
        body = {"model": model, "messages": [{"role": "user", "content": payload.prompt}]}
        r = requests.post(url, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=20)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"OpenAI 오류: {r.text}")
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return AiTestOut(provider="openai", model=model, output_text=text)
    

# ---------------- 담임반 선택 ----------------
class HomeroomIn(BaseModel):
    school_year: int = Field(..., ge=2000, le=2100)
    grade: int = Field(..., ge=1, le=3)
    class_no: int = Field(..., ge=1, le=30)

class HomeroomOut(BaseModel):
    id: int
    school_year: int
    grade: int
    class_no: int

def _this_year() -> int:
    return datetime.now().year

@router.get("/me/homeroom", response_model=Optional[HomeroomOut], dependencies=[Depends(role_required("teacher","admin"))])
def get_my_homeroom(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    현재 사용자(교사)의 지정 학년도 담임반을 반환 (없으면 null)
    - 기본 year=올해
    """
    y = year or _this_year()
    row = (
        db.query(HomeroomAssignment)
        .filter(
            HomeroomAssignment.school_year == y,
            HomeroomAssignment.teacher_user_id == current.id,
        )
        .first()
    )
    return row  # pydantic이 응답 스키마로 변환

@router.put("/me/homeroom", response_model=HomeroomOut, dependencies=[Depends(role_required("teacher","admin"))])
def set_my_homeroom(
    payload: HomeroomIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    담임반 배정/변경 (업서트)
    - 같은 학년도/학반이 이미 '다른' 교사에게 배정돼 있으면 409
    - 같은 학년도에 내가 이미 갖고 있으면 grade/class_no만 갱신
    """
    # 대상 학반이 이미 다른 교사에게 배정되어 있는지 확인
    occupied = (
        db.query(HomeroomAssignment)
        .filter(
            HomeroomAssignment.school_year == payload.school_year,
            HomeroomAssignment.grade == payload.grade,
            HomeroomAssignment.class_no == payload.class_no,
        )
        .first()
    )
    if occupied and occupied.teacher_user_id != current.id:
        raise HTTPException(status_code=409, detail="이미 다른 교사가 배정한 학반입니다.")

    mine = (
        db.query(HomeroomAssignment)
        .filter(
            HomeroomAssignment.school_year == payload.school_year,
            HomeroomAssignment.teacher_user_id == current.id,
        )
        .first()
    )
    if mine:
        # 내 학년도 배정을 해당 학반으로 이동
        mine.grade = payload.grade
        mine.class_no = payload.class_no
        db.commit(); db.refresh(mine)
        return mine

    # 새 배정
    new_row = HomeroomAssignment(
        school_year=payload.school_year,
        grade=payload.grade,
        class_no=payload.class_no,
        teacher_user_id=current.id,
    )
    db.add(new_row); db.commit(); db.refresh(new_row)
    return new_row