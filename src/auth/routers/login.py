import hashlib
from typing import Annotated
from fastapi import APIRouter, Depends,HTTPException,status
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import os

from pydantic import BaseModel

from src.database import PgDatabase

router=APIRouter(
    prefix='/users',
    tags=['users'],
)

class Login(BaseModel):
    email:str
    password:str


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
PUBLIC_SECRET_KEY = os.getenv('PUBLIC_SECRET_KEY')
PUBLIC_ALGORITHM = os.getenv('PUBLIC_ALGORITHM')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

ACCESS_TOKEN_EXPIRE_MINUTES= 30

class Users(BaseModel):
    id: int
    first_name: str
    last_name:str
    email: str

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


# Utility functions for the routes/////////////////////////////////

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
    expire = timedelta(minutes=60 ) + datetime.utcnow()
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
        token_data = TokenData(id=id)
    except JWTError as e:
        print(e)
        raise credentials_exception
    return token_data


def verify_refresh_token(token:str):
    credential_exception = HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}        
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)

        id:str = payload.get("id")
        if id is None:
            raise credential_exception
        token_data = TokenData(id=id)
    except JWTError as e:
        print('refresh',e)
        raise credential_exception
    return token_data

def check_and_delete_refresh_token(user_id: int):
    with PgDatabase() as db:
        # Check if the refresh token exists for the user
        db.cursor.execute(f"""
        SELECT id FROM refresh_token WHERE user_id = '{str(user_id)}';
        """)
        refresh_token = db.cursor.fetchone()

        # If a refresh token is found, delete it
        if refresh_token:
            db.cursor.execute(f"""
            DELETE FROM refresh_token WHERE user_id = '{str(user_id)}';
            """)
            db.connection.commit()


def getUser(email):
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT * 
                         FROM users where email='{str(email)}';""")
        user = db.cursor.fetchone()
        if user==None:
            return None
        return user

def add_refresh_token(refresh_token_dict: dict):
    with PgDatabase() as db:
        user_id=refresh_token_dict['user_id']
        refresh_token=refresh_token_dict['refresh_token']
        db.cursor.execute(f"""
        INSERT INTO refresh_token (user_id, refresh_token)
        VALUES ('{user_id}', '{refresh_token}')
        RETURNING id;
        """)
        db.connection.commit()
        inserted_id = db.cursor.fetchone()[0]
    return inserted_id


def check_refresh_token(user_id: int):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        SELECT refresh_token FROM refresh_token WHERE user_id = '{user_id}';
        """)
        refresh_token = db.cursor.fetchone()
        if refresh_token!=None:
            return refresh_token
        return None
    

def check_and_delete_refresh_token_for_refresh(user_id: int, provided_token: str):
    with PgDatabase() as db:
        # Check if the refresh token exists for the user
        db.cursor.execute(f"""
        SELECT refresh_token FROM refresh_token WHERE user_id = '{user_id}';
        """)
        result = db.cursor.fetchone()

        if not result:
            raise HTTPException(status_code=401, detail="No refresh token found for the user")

        existing_token = result[0]

        if existing_token != provided_token:
            # Delete the existing token
            db.cursor.execute(f"""
            DELETE FROM refresh_token WHERE user_id = '{user_id}';
            """)
            db.connection.commit()

            raise HTTPException(status_code=401, detail="Refresh tokens do not match")
        else:
            # Delete the existing token
            db.cursor.execute(f"""
            DELETE FROM refresh_token WHERE user_id = '{user_id}';
            """)
            db.connection.commit()
    


#Routes//////////////////////////////////////////////////////////////////////////////////////

@router.post('/login')
def login(data: Login):
    email = data.email.replace(" ", "")
    password = data.password.replace(" ", "")
    user = getUser(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId=user[0]
    firstName=user[1]
    lastName=user[2]
    userEmail=user[3]
    userPassword=user[4]
    if not verify_password(userPassword, password, "Your Salt"):
        raise HTTPException(status_code=404, detail="Incorrect password")
    check_and_delete_refresh_token(userId)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={ "id": userId}, expires_delta=access_token_expires
    )
    refresh_token=create_refresh_token(data={"id": userId})
    
    refresh_token_dict = {
        "user_id": userId,
        "refresh_token": refresh_token,
    }   
    try:
        add_refresh_token(refresh_token_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    returnData={
        'first_name':firstName,
        'last_name':lastName,
        'email':userEmail,
        'id':userId

    }
    return Token(user=returnData, access_token=access_token,refresh_token=refresh_token, token_type="bearer")


            

@router.get("/refresh", status_code=status.HTTP_200_OK)
def get_new_access_token(token:str):
    token_data = verify_refresh_token(token)
    # refresh_token_check = db.query(RefreshToken).filter(RefreshToken.user_id == token_data.id)
    check_and_delete_refresh_token_for_refresh(token_data.id,token)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token= create_access_token({"id": token_data.id},expires_delta=access_token_expires)
    new_refresh_token=create_refresh_token(data={"id": token_data.id})

    refresh_token_dict = {
        "user_id": token_data.id,
        "refresh_token": new_refresh_token,
    }
    try:
        add_refresh_token(refresh_token_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


    return {
        "access_token": new_access_token,
        "refresh_token":new_refresh_token,
        "token_type":"Bearer",
        "status": status.HTTP_200_OK
    }


#login for the api docs
@router.post('/token')
def login(data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    email = data.username.replace(" ", "")
    password = data.password.replace(" ", "")
    user = getUser(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId=user[0]
    firstName=user[1]
    lastName=user[2]
    userEmail=user[3]
    userPassword=user[4]
    if not verify_password(userPassword, password, "Your Salt"):
        raise HTTPException(status_code=404, detail="Incorrect password")
    check_and_delete_refresh_token(userId)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={ "id": userId}, expires_delta=access_token_expires
    )
    refresh_token=create_refresh_token(data={"id": userId})
    
    refresh_token_dict = {
        "user_id": userId,
        "refresh_token": refresh_token,
    }   
    try:
        add_refresh_token(refresh_token_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    returnData={
        'first_name':firstName,
        'last_name':lastName,
        'email':userEmail,
        'id':userId

    }
    return Token(user=returnData, access_token=access_token,refresh_token=refresh_token, token_type="bearer")
