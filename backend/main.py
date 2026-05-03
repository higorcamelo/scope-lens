from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def api_status():
  return {"message": "Scope Lens API is running!"}
