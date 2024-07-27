from fastapi import APIRouter,HTTPException,status,UploadFile,File
from psycopg2.errors import DatetimeFieldOverflow, OperationalError
from src.database import PgDatabase
from typing import Literal, Optional
from datetime import datetime
import pandas as pd
from io import BytesIO


from pydantic import BaseModel


router=APIRouter(
    prefix='/artist',
    tags=['artist'],
)


class Artists(BaseModel):
    id:Optional[int|None]=None
    name:str
    gender:Literal['m', 'f', 'o']
    address:str
    no_of_albums_released:int
    dob:datetime

artist='artist'

def count_t_artist():
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT *
                         FROM artist ORDER BY created_at DESC;""")
        artists = [
            {
                "id": data[0],
                "name": data[1],
                "gender":data[2],
                "address":str(data[3]),
                "no_of_albums_released":data[4],
                "dob":data[5],
            }
            for data in db.cursor.fetchall()
        ]
    return artists

def select_t_artist(page):
    limit = 5
    offset = (page - 1) * limit
    
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT *
                         FROM artist ORDER BY created_at DESC
                          LIMIT {limit}
                            OFFSET {offset}
                          ;""")
        artists = [
            {
                "id": data[0],
                "name": data[1],
                "gender":data[2],
                "address":str(data[3]),
                "no_of_albums_released":data[4],
                "dob":data[5],
            }
            for data in db.cursor.fetchall()
        ]
    return artists

def insert_t_artist(payload: Artists, *args, **kwargs):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        INSERT INTO artist (name, address, gender,no_of_albums_released,dob,created_at, updated_at) 
        VALUES('{payload.name}', 
                '{payload.address}', 
                '{payload.gender}',
                '{payload.no_of_albums_released}',
                '{payload.dob}',
                NOW(),
                NOW()
                ) 
        RETURNING id;
                    """)
        db.connection.commit()
        inserted_id = db.cursor.fetchone()[0]

        obj = select_t_artist_by_id(inserted_id)
    return obj

def select_t_artist_by_id(id: int) -> dict:
    with PgDatabase() as db:
        db.cursor.execute(f"""
        SELECT * FROM artist
        WHERE id='{id}';
                        """)
        data = db.cursor.fetchone()
        if data is None:
            return None

    return {
        "id": data[0],
        "name": data[1],
        "gender":data[2],
        "address":str(data[3]),
        "no_of_albums_released":data[4],
        "dob":data[5],
    }


def update_t_artist_by_id(id: int, payload: Artists):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        UPDATE artist
        SET name='{payload.name}', 
            gender='{payload.gender}', 
            address='{payload.address}',
            no_of_albums_released='{payload.no_of_albums_released}',
            dob='{payload.dob}'
        WHERE id='{id}'
        RETURNING id;
                        """)
        db.connection.commit()
        result = db.cursor.fetchone()
        if not result:
            return None
        updated_id = result[0]
        obj = select_t_artist_by_id(updated_id)
    return obj

def delete_t_artist_by_id(id: int):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        DELETE FROM artist
        WHERE id='{id}';
                        """)
        db.connection.commit()
        res = db.cursor.statusmessage
    if res == "DELETE 1":
        return True
    return False

@router.get('/getArtists/{pageNumber}')
def getArtists(pageNumber:int):
    try:
        count=len(count_t_artist())
        totalCount=0
        if count==5:
            totalCount=1
        else:
            if count%5==0:
                totalCount=count/5
            else:
                totalCount=(count//5)+1

        return {'count':totalCount,'data':select_t_artist(pageNumber)} 
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="""Check if the database exists, connection is successful or tables exist. To create tables use '/initdb' endpoint"""
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"""Error {e}"""
        )
    
@router.post('/createArtists')
def createArtists(artistData:Artists):
    return insert_t_artist(artistData)

@router.put('/updateArtistById/{id}/', status_code=status.HTTP_200_OK)
async def update_artist_by_id(payload: Artists, id: int ):
    result = update_t_artist_by_id(id, payload)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return {'message':"Artist has been updated", 'result':result}
    
@router.get('/getArtistById/{id}')
def getArtistById(id:int):
    result = select_t_artist_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return result

@router.delete('/deleteArtistById/{id}/')
async def delete_artist_by_id(id: int ):
    result = delete_t_artist_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return {'message':'Artist successfully removed'}



@router.post("/upload-artists/")
async def upload_artists(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel file.")
    
    content = await file.read()
    data = pd.read_excel(BytesIO(content))
    
    required_columns = ["name", "gender", "address", "no_of_albums_released", "dob"]
    if not all(column in data.columns for column in required_columns):
        raise HTTPException(status_code=400, detail="Excel file is missing required columns.")
    
    records = data[required_columns].to_dict(orient='records')
    
    with PgDatabase() as db:
            for record in records:
                db.cursor.execute(f"""
                    INSERT INTO artist (name, gender, address, no_of_albums_released, dob)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (record['name'], record['gender'], record['address'], record['no_of_albums_released'], record['dob']))
            db.connection.commit()
    
    return {"detail": "Artists data uploaded successfully"}