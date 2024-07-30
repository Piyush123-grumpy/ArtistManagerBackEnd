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
        database_url = os.getenv("POSTGRES_SERVER")
        if not database_url:
            raise ValueError("No DATABASE_URL set for PostgreSQL connection")

        # commented for live purposes
        # return self.driver.connect(database_url)
        return self.driver.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB")
        )
    
users='users'
artist='artist'
music='music'
refreshToken='refresh_token'

# Put these query at the initial time of building the tables


def create_tables():
    with PgDatabase() as db:
        db.cursor.execute(f"""
            CREATE TYPE gender AS ENUM ('m', 'f', '0');
            CREATE TYPE genre AS ENUM ('rock', 'rnb', 'country', 'classic', 'jazz');  
            CREATE TABLE {users} (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(20) UNIQUE NOT NULL,
                dob DATE NOT NULL,
                gender GENDER NOT NULL,
                address VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE {artist} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                gender GENDER NOT NULL,
                address VARCHAR(255) NOT NULL,
                first_release_year VARCHAR(255) NOT NULL,
                no_of_albums_released INTEGER NOT NULL,
                dob DATE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE {music} (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                album_name VARCHAR(255) NOT NULL,
                genre GENRE NOT NULL,
                artist_id INTEGER REFERENCES artist(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE {refreshToken} (
                id SERIAL PRIMARY KEY,
                refresh_token VARCHAR(255) NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW()
            );

        """)
        db.connection.commit()
        print("Tables are created successfully...")

def drop_tables():
    with PgDatabase() as db:
        db.cursor.execute(f"DROP TABLE IF EXISTS {users} CASCADE;")
        db.cursor.execute(f"DROP TABLE IF EXISTS {artist} CASCADE;")
        db.cursor.execute(f"DROP TABLE IF EXISTS {music} CASCADE;")
        db.cursor.execute(f"DROP TABLE IF EXISTS {refreshToken} CASCADE;")
        db.cursor.execute("DROP TYPE IF EXISTS gender;")
        db.cursor.execute("DROP TYPE IF EXISTS genre;")
        db.connection.commit()
        print("Tables are dropped...")