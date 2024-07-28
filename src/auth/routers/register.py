import hashlib
from fastapi.responses import JSONResponse
from fastapi import APIRouter,HTTPException,status
import re
from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from psycopg2.errors import DatetimeFieldOverflow
from psycopg2 import sql, errors
from datetime import datetime
from src.database import PgDatabase


router=APIRouter(
    prefix='/users',
    tags=['users'],
)

uppercase_pattern = re.compile(r"[A-Z]")
special_character_pattern = re.compile(r"[@$!%*?&]")
digit_pattern = re.compile(r"\d")

salt="Your Salt"
class UserRegistration(BaseModel):
    first_name:str
    last_name:str
    email: EmailStr
    password: str
    confirm_password: str
    phone: str = Field(..., pattern="^\d{10}$")  # Validating for a 10-digit phone number
    address: str
    gender_select: Literal['m', 'f', 'o']  # 'm' for male, 'f' for female, 'o' for other
    date_time: datetime


def validate_password(password: str):
    not_met_criteria = []
    if not uppercase_pattern.search(password):
        not_met_criteria.append("uppercase")
    if not special_character_pattern.search(password):
        not_met_criteria.append("special character")
    if not digit_pattern.search(password):
        not_met_criteria.append("digit")
    if len(not_met_criteria) > 0:
        return JSONResponse(
            status_code=400,
            # content={"valid": False, "criteria_not_met": not_met_criteria}
            content={"detail": [{
                "type": "value_error",
                "loc": [
                    "body",
                    "password"
                ],
                "msg": f"Value is not a valid password: The password is not valid. It must have {not_met_criteria[0]}",
                "input": password,
                "ctx": {
                    "reason": "The email address is not valid. It must have exactly one @-sign."
                }}]
            }
        )
    else:
        return True
    
def email_exists(email):
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT * 
                         FROM users where email='{str(email)}';""")
        user = db.cursor.fetchone()
        return user is not None

def insert_user(payload: UserRegistration) -> dict:
    with PgDatabase() as db:
        try:
            db.cursor.execute(f"""
            INSERT INTO users (
                first_name, last_name, email, password, phone, dob, gender, address, created_at, updated_at
            ) VALUES (
                '{payload.first_name}',
                '{payload.last_name}',
                '{payload.email}',
                '{payload.password}',
                '{payload.phone}',
                '{payload.date_time}',
                '{payload.gender_select}',
                '{payload.address}',
                NOW(),
                NOW()
            ) RETURNING id;
            """)
            db.connection.commit()
            inserted_id = db.cursor.fetchone()[0]
        except errors.UniqueViolation as e:
            if 'users_email_key' in str(e):
                raise HTTPException(status_code=500, detail={
                    "email": "User already exists with this email address"})
            elif 'users_phone_key' in str(e):
                raise HTTPException(status_code=500, detail={'phone':"User already exists with this phone number"})
            else:
                raise HTTPException(status_code=500, detail="A unique constraint violation occurred")
    # Return the inserted user ID or any other required info
    return {"id": inserted_id}
    

@router.post('/register/',tags=['users'])
def register_user(data:UserRegistration):
    password=data.password
    with PgDatabase() as db:
        if validate_password(password):
            if validate_password(password) != True:
                return validate_password(password)
            password_hash = hashlib.sha256(
            (password + salt).encode('utf-8')).hexdigest()
            data.password=password_hash
            try:
                if email_exists(data.email):
                    return JSONResponse(
                    status_code=500,
                        content={
                           "detail": {
                                "email":"User already exists with this email address"
                            }
                    }
                    )
                insert_user(data)
                return {'message':'User registered succefully'}
                # print(insert_user(data))
            except DatetimeFieldOverflow:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formats are : month-day-year hour:minute:seconds or year-month-day hour:minute:seconds"
                    )
            except Exception as e:
                raise e
       
    return {'message':'user registered'}