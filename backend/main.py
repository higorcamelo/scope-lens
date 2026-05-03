from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
  return {"message": "Scope Lens API is running!"}
