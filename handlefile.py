# handlefile.py

from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
from parse_resume import parse_resume

router = APIRouter()
FILE_PATH = "data/resume.pdf"  # Constant for file path


# =======================
# Upload Resume Endpoint
# =======================
@router.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        os.makedirs("data", exist_ok=True)

        # Always overwrite the file if it exists
        with open(FILE_PATH, "wb") as f:
            shutil.copyfileobj(file.file, f)

        structured = parse_resume()

        return {"status": "Resume uploaded successfully", "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the file: {str(e)}")



# =======================
# Delete Resume Endpoint
# =======================
@router.delete("/delete-resume/")
def delete_resume():
    try:
        if not os.path.exists(FILE_PATH):  # Check if file exists before deleting
            raise HTTPException(status_code=404, detail="File not found. No file exists to delete.")

        confirmation = input("Are you sure you want to delete the file? Type 'yes' to confirm: ")

        if confirmation.lower() != 'yes':
            return {"status": "File deletion cancelled"}

        os.remove(FILE_PATH)  # Delete the file
        return {"status": "File deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the file: {str(e)}")
