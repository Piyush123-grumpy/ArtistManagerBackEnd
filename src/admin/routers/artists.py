from fastapi import APIRouter, Depends,HTTPException,status,UploadFile,File
from psycopg2.errors import DatetimeFieldOverflow, OperationalError
from src.database import PgDatabase
from typing import Literal, Optional
from src.auth.routers.login import oauth2_scheme,verify_token_access
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
    first_release_year:str
    address:str
    no_of_albums_released:int
    dob:datetime

artist='artist'


#sql query for counting all the data in artist table
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

#Sql query for selcting data with limit and offset for pagination pruposes
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
                "first_release_year":str(data[4]),
                "no_of_albums_released":data[5],
                "dob":data[6],
            }
            for data in db.cursor.fetchall()
        ]
    return artists

#sql query for inserint data into the artist table
def insert_t_artist(payload: Artists, *args, **kwargs):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        INSERT INTO artist (name, address,first_release_year, gender,no_of_albums_released,dob,created_at, updated_at) 
        VALUES('{payload.name}', 
                '{payload.address}', 
                '{payload.first_release_year}',
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

#sql query for selecting artist's by id
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
        "first_release_year":str(data[4]),

        "no_of_albums_released":data[5],
        "dob":data[6],
    }

#sql query for updating artist's by id
def update_t_artist_by_id(id: int, payload: Artists):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        UPDATE artist
        SET name='{payload.name}', 
            gender='{payload.gender}', 
            address='{payload.address}',
            first_release_year='{payload.first_release_year}',
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

#sql query for deleting artist's by id
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


#API ENDPOINTS FOR CURD OPERATONS OF ARTIST'S
@router.get('/getArtists/{pageNumber}')
def getArtists(pageNumber:int,token:str=Depends(oauth2_scheme)):
    verify_token_access(token)
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
def createArtists(artistData:Artists,token:str=Depends(oauth2_scheme)):
    verify_token_access(token)
    return insert_t_artist(artistData)

@router.put('/updateArtistById/{id}/', status_code=status.HTTP_200_OK)
async def update_artist_by_id(payload: Artists, id: int,token:str=Depends(oauth2_scheme) ):
    verify_token_access(token)
    result = update_t_artist_by_id(id, payload)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return {'message':"Artist has been updated", 'result':result}
    
@router.get('/getArtistById/{id}')
def getArtistById(id:int,token:str=Depends(oauth2_scheme)):
    verify_token_access(token)

    result = select_t_artist_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return result

@router.delete('/deleteArtistById/{id}/')
async def delete_artist_by_id(id: int ,token:str=Depends(oauth2_scheme)):
    verify_token_access(token)

    result = delete_t_artist_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Artist not found')
    return {'message':'Artist successfully removed'}


#Excel file upload code
@router.post("/upload-artists/")
async def upload_artists(file: UploadFile = File(...),token:str=Depends(oauth2_scheme)):
    verify_token_access(token)
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel file.")
    
    content = await file.read()
    data = pd.read_excel(BytesIO(content))
    
    required_columns = ["name", "gender","first_release_year", "address", "no_of_albums_released", "dob"]
    if not all(column in data.columns for column in required_columns):
        raise HTTPException(status_code=400, detail="Excel file is missing required columns.")
    
    records = data[required_columns].to_dict(orient='records')
    
    with PgDatabase() as db:
            try:
                for record in records:
                    try:
                        dob = datetime.strptime(str(record['dob']), '%Y-%m-%d %H:%M:%S' ).date()
                    except ValueError:
                        raise HTTPException(status_code=400, detail=f"Invalid date format for dob: {record['dob']}. Expected format is YYYY-MM-DD.")
                    db.cursor.execute(f"""
                        INSERT INTO artist (name, gender,first_release_year, address, no_of_albums_released, dob,created_at,updated_at)
                        VALUES ('{record['name']}','{record['gender'].lower()}','{record['first_release_year']}','{record['address']}','{record['no_of_albums_released']}','{dob}',NOW(),
                    NOW())
                        ON CONFLICT DO NOTHING;
                    """)
                db.connection.commit()
            except Exception as e:
                error_message = str(e)
                if 'invalid input value for enum gender' in error_message:
                    raise HTTPException(status_code=400, detail="Invalid value for gender. Please use valid f , m ,o values.")
                elif 'invalid input syntax for type integer' in error_message:
                    raise HTTPException(status_code=400, detail="Invalid value for no_of_albums_released. Please use valid numerical values.")
                elif '400: Invalid date format for dob: asd. Expected format is YYYY-MM-DD.' in error_message:
                    raise HTTPException(status_code=400, detail=f"Invalid date format for dob: {record['dob']}. Expected format is YYYY-MM-DD HH:MM:SS.")
                else:
                    raise HTTPException(status_code=500, detail="Failed to upload data to the database.") from e
    
    
    return {"detail": "Artists data uploaded successfully"}