# security.py (업데이트)
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ✅ .env에서 불러오기 (기본값은 개발용 임시값)
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_ENV")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# 상담 암호화용 키 (반드시 .env에서 제공 권장)
_COUNSEL_KEY = os.getenv("COUNSEL_SECRET_KEY")
_f = Fernet(_COUNSEL_KEY.encode()) if _COUNSEL_KEY else None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, extra_claims: Optional[dict] = None,
                        expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = {
        "sub": subject,
        "iat": int(datetime.now(tz=timezone.utc).timestamp()),
        "exp": int((datetime.now(tz=timezone.utc) + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# ---------- 상담 암호화 유틸 ----------
def encrypt_text(plain: Optional[str]) -> Optional[str]:
    if plain is None:
        return None
    if not _f:
        # 개발 환경 보호: 키 미설정일 땐 평문 저장 (운영에선 반드시 키 설정)
        return plain
    return _f.encrypt(plain.encode()).decode()

def decrypt_text(cipher: Optional[str]) -> Optional[str]:
    if cipher is None:
        return None
    if not _f:
        return cipher
    try:
        return _f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        # 과거 평문 데이터가 섞여있을 수 있으니 안전 복호화
        return cipher
