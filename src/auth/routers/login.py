import hashlib
from fastapi import APIRouter,HTTPException,status
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import os

from pydantic import BaseModel

router=APIRouter(
    prefix='/users',
    tags=['users'],
)

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
PUBLIC_SECRET_KEY = os.getenv('PUBLIC_SECRET_KEY')
PUBLIC_ALGORITHM = os.getenv('PUBLIC_ALGORITHM')

class Users(BaseModel):
    id: int
    user_name: str
    email: str
    smsCredit: int
    rate: float
    userRole: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    user: Users
    access_token: str
    token_type: str
    refresh_token:str


class TokenData(BaseModel):
    username: str | None = None
    id: int | None = None
    userRole: str | None = None

def verify_password(stored_password, provided_password, salt):
    password_hash = hashlib.sha256(
        (provided_password + salt).encode('utf-8')).hexdigest()
    return password_hash == stored_password

def create_access_token(data: dict, expires_delta: timedelta | None = None, public=False):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) if not public else jwt.encode(
        to_encode, PUBLIC_SECRET_KEY, algorithm=PUBLIC_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data:dict):
    to_encode = data.copy()
    expire = timedelta(minutes=60) + datetime.utcnow()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token_access(token: str, public=False):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) if not public else jwt.decode(
            token, PUBLIC_SECRET_KEY, algorithms=[PUBLIC_ALGORITHM])
        id: str = payload.get('id')
        username: str = payload.get("sub")
        userRole: str = payload.get('user_type')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, id=id, userRole=userRole)
    except JWTError:
        raise credentials_exception
    return token_data
    # user = get_user(fake_users_db, username=token_data.username)
    # if user is None:
    #     raise credentials_exception
    # return user


def verify_refresh_token(token:str):
    credential_exception = HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}        
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)

        id:str = payload.get("id")
        username: str = payload.get("sub")
        userRole: str = payload.get('user_type')
        if id is None:
            raise credential_exception
        token_data = TokenData(id=id,username=username,userRole=userRole)
    except JWTError:
        raise credential_exception
    return token_data

@router.get("/login")
def login():
    return {"message": "Hello World"}