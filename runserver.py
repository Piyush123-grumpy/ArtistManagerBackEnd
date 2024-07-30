from src import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    #i suggest running from the terminal with uvicorn main:app --reload command as this was created for deployment
    uvicorn.run(app="src:app", port=8000, reload=True)