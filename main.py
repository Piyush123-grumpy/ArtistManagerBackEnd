from fastapi import FastAPI,status 
from fastapi.exceptions import HTTPException
from src.admin.routers import users
from src.auth.routers import login,register
from src.admin.routers import artists,music
from fastapi.middleware.cors import CORSMiddleware
from src.database import drop_tables, create_tables # new
app = FastAPI()

origins=[
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router)
app.include_router(register.router)
app.include_router(artists.router)
app.include_router(music.router)
app.include_router(users.router)

@app.post('/initdb')
async def initdb():
    try:
        drop_tables()
        create_tables()
        return {"message": "Tables dropped and created!"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error {e}"
        )