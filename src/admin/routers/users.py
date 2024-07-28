from datetime import datetime
from fastapi import APIRouter, Depends,HTTPException,status
from src.auth.routers.login import oauth2_scheme,verify_token_access
from pydantic import BaseModel, EmailStr, Field
from src.database import PgDatabase
from typing import Literal, Optional
from psycopg2 import sql, errors



router=APIRouter(
    prefix='/users',
    tags=['users'],
)


class UserEdit(BaseModel):
    first_name:str
    last_name:str
    email: EmailStr
    phone: str = Field(..., pattern="^\d{10}$")  # Validating for a 10-digit phone number
    address: str
    gender: Literal['m', 'f', 'o']  # 'm' for male, 'f' for female, 'o' for other
    date_time: datetime


def select_t_user_by_id(id: int) -> dict:
    with PgDatabase() as db:
        db.cursor.execute(f"""
        SELECT * FROM users
        WHERE id='{id}';
                        """)
        data = db.cursor.fetchone()
        if data is None:
            return None

    return {
        "first_name": data[1],
        "last_name": data[2],
        "email":data[3],
        "phone":data[5],
        "date_time":data[6],
        "gender":data[7],
        "address":str(data[8]),
    }

def update_t_user_by_id(id: int, payload: UserEdit):
    with PgDatabase() as db:
        try:
            db.cursor.execute(f"""
            UPDATE users
            SET first_name='{payload.first_name}', 
                last_name='{payload.last_name}', 
                email='{payload.email}',
                phone='{payload.phone}',
                dob='{payload.date_time}',
                gender='{payload.gender}',
                address='{payload.address}'
            WHERE id='{id}'
            RETURNING id;
                            """)
            db.connection.commit()
            result = db.cursor.fetchone()
            if not result:
                return None
            updated_id = result[0]
            obj = select_t_user_by_id(updated_id)
        except errors.UniqueViolation as e:
            if 'users_email_key' in str(e):
                raise HTTPException(status_code=500, detail={
                    "email": "User already exists with this email address"})
            elif 'users_phone_key' in str(e):
                raise HTTPException(status_code=500, detail={'phone':"User already exists with this phone number"})
            else:
                raise HTTPException(status_code=500, detail="A unique constraint violation occurred")
    return obj


@router.get('/getUserById/{id}')
def getUserById(id:int,token:str=Depends(oauth2_scheme)):
    verify_token_access(token)

    result = select_t_user_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return result

@router.put('/updateUserById/{id}/', status_code=status.HTTP_200_OK)
async def update_artist_by_id(payload: UserEdit, id: int,token:str=Depends(oauth2_scheme) ):
    verify_token_access(token)
    result = update_t_user_by_id(id, payload)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return {'message':"User has been updated", 'result':result}