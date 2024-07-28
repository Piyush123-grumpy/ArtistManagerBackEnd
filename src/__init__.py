from fastapi import FastAPI,status
# from src.auth.auth_routes import auth_router
# from src.config import Settings
from contextlib import asynccontextmanager
# from src.config import settings
# from src.db import init_db
from fastapi.middleware.cors import CORSMiddleware
from src.admin.routers import users
from src.auth.routers import login,register
from src.admin.routers import artists,music
from src.database import drop_tables, create_tables # new
from fastapi.exceptions import HTTPException



# lifespan code

@asynccontextmanager
async def lifespan(app:FastAPI):
    await initdb()

    yield

def create_app():
    app = FastAPI( description="This is a simple REST API for a artist manager",
        title="Artist Manager",
        version="V1",
        lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(login.router)
    app.include_router(register.router)
    app.include_router(artists.router)
    app.include_router(music.router)
    app.include_router(users.router)
    return app


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


app = create_app()