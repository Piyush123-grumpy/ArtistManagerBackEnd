from fastapi import FastAPI
from src.auth.routers import login
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
async def root():
    return {"message": "Hello World"}