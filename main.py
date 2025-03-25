# main.py

from fastapi import FastAPI
from pydantic import BaseModel
import os
import uvicorn

from handlefile import router as file_router  # Importing the router from handlefile
from dataexcel import router as excel_router
from parse_resume import router as parse_router


app = FastAPI(title="Minimal AI Job Agent")

# ========== Models ==========

class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    veteran_status: str = "Not a Veteran"
    disability_status: str = "None"

# ========== Routers ==========

# Include the router for handling file uploads
app.include_router(file_router)
app.include_router(excel_router)
app.include_router(parse_router)

# ========== Endpoints ==========

@app.get("/")
def root():
    return {"message": "AI Job Agent is running."}

@app.post("/upload-profile/")
def upload_profile(profile: UserProfile):
    os.makedirs("data", exist_ok=True)
    with open("data/user_profile.json", "w") as f:
        f.write(profile.json(indent=2))
    return {"status": "Profile saved", "name": profile.name}

# ========== Main App Runner ==========

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
