from fastapi import APIRouter,HTTPException,status
from psycopg2.errors import DatetimeFieldOverflow, OperationalError
from src.database import PgDatabase
from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel


router=APIRouter(
    prefix='/music',
    tags=['music'],
)


class Music(BaseModel):
    id:Optional[int|None]=None
    artist_id:Optional[int|None]=None
    title:str
    genre:Literal['rock','rnb', 'country', 'classic','jazz']
    album_name:str

music='music'

def count_t_music(artist_id:int):
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT *
                         FROM music WHERE artist_id='{artist_id}' ORDER BY created_at DESC;""")
        artists = [
            {
                "id": data[0],
                "title": data[1],
                "album_name":data[2],
                "genre":data[3],
                "artist_id":str(data[4]),
            }
            for data in db.cursor.fetchall()
        ]
    return artists

def select_t_music(artist_id:int,page:int):
    limit = 5
    offset = (page - 1) * limit
    with PgDatabase() as db:
        db.cursor.execute(f"""SELECT *
                         FROM music WHERE artist_id='{artist_id}' ORDER BY  created_at DESC LIMIT {limit}
                            OFFSET {offset}  ;""")
        artists = [
            {
                "id": data[0],
                "title": data[1],
                "album_name":data[2],
                "genre":data[3],
                "artist_id":str(data[4]),
            }
            for data in db.cursor.fetchall()
        ]
    return artists

def insert_t_music(payload: Music, *args, **kwargs):
    with PgDatabase() as db:
        print(payload)
        db.cursor.execute(f"""
        INSERT INTO music (artist_id, title, album_name,genre,created_at, updated_at) 
        VALUES('{payload.artist_id}', 
                '{payload.title}', 
                '{payload.album_name}',
                '{payload.genre}',
                NOW(),
                NOW()
                ) 
        RETURNING id;
                    """)
        db.connection.commit()
        inserted_id = db.cursor.fetchone()[0]

        obj = select_t_music_by_id(inserted_id)
    return obj

def select_t_music_by_id(id: int) -> dict:
    with PgDatabase() as db:
        db.cursor.execute(f"""
        SELECT * FROM music
        WHERE id='{id}';
                        """)
        data = db.cursor.fetchone()
        if data is None:
            return None

    return {
        "id": data[0],
        "title": data[1],
        "album_name":data[2],
        "genre":data[3],
        "artist_id":str(data[4]),
    }


def update_t_music_by_id(id: int, payload: Music):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        UPDATE music
        SET title='{payload.title}', 
            album_name='{payload.album_name}', 
            genre='{payload.genre}',
            artist_id='{payload.artist_id}'
        WHERE id='{id}'
        RETURNING id;
                        """)
        db.connection.commit()
        result = db.cursor.fetchone()
        if not result:
            return None
        updated_id = result[0]
        obj = select_t_music_by_id(updated_id)
    return obj

def delete_t_music_by_id(id: int):
    with PgDatabase() as db:
        db.cursor.execute(f"""
        DELETE FROM music
        WHERE id='{id}';
                        """)
        db.connection.commit()
        res = db.cursor.statusmessage
    if res == "DELETE 1":
        return True
    return False



@router.get('/getMusic/{id}/{pageNumber}')
def getMusic(id:int,pageNumber:int):
    try:
        count=len(count_t_music(id))
        totalCount=0
        if count==5:
            totalCount=1
        else:
            if count%5==0:
                totalCount=count/5
            else:
                totalCount=(count//5)+1
        return {'count':totalCount ,'data':select_t_music(id,pageNumber)} 
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
    

@router.post('/createMusic')
def createMusic(musicData:Music):
    return insert_t_music(musicData)

@router.put('/updateMusicById/{id}/', status_code=status.HTTP_200_OK)
async def update_music_by_id(payload: Music, id: int ):
    result = update_t_music_by_id(id, payload)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Music not found')
    return {'message':"Music has been updated", 'result':result}

    
@router.get('/getMusicById/{id}')
def getArtistById(id:int):
    result = select_t_music_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Music not found')
    return result

@router.delete('/deleteMusicById/{id}/')
async def delete_music_by_id(id: int ):
    result = delete_t_music_by_id(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Music not found')
    return {'message':'Music successfully removed'}