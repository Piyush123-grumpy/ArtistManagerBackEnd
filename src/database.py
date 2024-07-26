import os
from pathlib import Path
import dotenv
from abc import ABC, abstractmethod # new
import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

class Database(ABC):
    """
    Database context manager
    """

    def __init__(self, driver) -> None:
        self.driver = driver

    @abstractmethod
    def connect_to_database(self):
        raise NotImplementedError()

    def __enter__(self):
        self.connection = self.connect_to_database()
        self.cursor = self.connection.cursor()
        return self

    def __exit__(self, exception_type, exc_val, traceback):
        self.cursor.close()
        self.connection.close()


class PgDatabase(Database):
    """PostgreSQL Database context manager"""

    def __init__(self) -> None:
        self.driver = psycopg2
        super().__init__(self.driver)

    def connect_to_database(self):
        return self.driver.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    
user='user'
artist='artist'
music='music'


def create_tables():
    with PgDatabase() as db:
        db.cursor.execute("""
            CREATE TYPE gender AS ENUM ('m', 'f', '0');
            CREATE TYPE genre AS ENUM ('rock', 'rnb', 'country', 'classic', 'jazz');
            
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                email VARCHAR(255),
                password VARCHAR(255),
                phone VARCHAR(20),
                dob DATE,
                gender GENDER,
                address VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE artist (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                phone VARCHAR(20),
                gender GENDER,
                address VARCHAR(255),
                no_of_albums_released INTEGER,
                dob DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE songs (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                duration INTEGER, -- Duration in seconds
                genre GENRE,
                release_date DATE,
                artist_id INTEGER REFERENCES artist(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        db.connection.commit()
        print("Tables are created successfully...")

def drop_tables():
    with PgDatabase() as db:
        db.cursor.execute(f"DROP TABLE IF EXISTS {user} CASCADE;")
        db.connection.commit()
        print("Tables are dropped...")