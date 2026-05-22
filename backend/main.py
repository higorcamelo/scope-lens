from fastapi import FastAPI
from app.api import router

app = FastAPI(
    title="Scope Lens",
    description="Replay analyzer for Pokémon Showdown",
    version="0.1.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message": "Scope Lens API is running"
    }