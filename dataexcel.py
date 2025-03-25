# Dataexcel.py

from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
import pandas as pd  # For reading Excel files
import webbrowser  # For opening links in the web browser


router = APIRouter()
FILE_PATH = "data/job_links.xlsx"  # Constant for the Excel file path


# =======================
# Upload Excel File Endpoint
# =======================
@router.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...)):
    try:
        os.makedirs("data", exist_ok=True)

        if os.path.exists(FILE_PATH):  # Check if file already exists
            print("An Excel file already exists.")
            choice = input("Do you want to (O)verwrite or (C)ancel the upload? [O/C]: ").strip().lower()

            if choice == 'c':  # Cancel
                return {"status": "Upload cancelled", "message": "File upload was not performed."}
            elif choice == 'o':  # Overwrite
                with open(FILE_PATH, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                return {"status": "Excel file overwritten successfully", "filename": file.filename}
            else:
                return {"status": "Invalid choice. Operation aborted."}

        # If the file doesn't exist, simply save it
        with open(FILE_PATH, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return {"status": "Excel file uploaded successfully", "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the Excel file: {str(e)}")


# =======================
# Delete Excel File Endpoint
# =======================
@router.delete("/delete-excel/")
def delete_excel():
    try:
        if not os.path.exists(FILE_PATH):  # Check if file exists before deleting
            raise HTTPException(status_code=404, detail="Excel file not found. No file exists to delete.")

        confirmation = input("Are you sure you want to delete the Excel file? Type 'yes' to confirm: ")

        if confirmation.lower() != 'yes':
            return {"status": "File deletion cancelled"}

        os.remove(FILE_PATH)  # Delete the file
        return {"status": "Excel file deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the Excel file: {str(e)}")


# =======================
# Read & Open Links From Excel
# =======================
@router.get("/open-links/")
def open_links():
    try:
        if not os.path.exists(FILE_PATH):
            raise HTTPException(status_code=404, detail="Excel file not found. Please upload the file first.")

        # Read the Excel file
        df = pd.read_excel(FILE_PATH)

        if "Application link" not in df.columns:
            raise HTTPException(status_code=400,
                                detail="The Excel file does not contain a column named 'Application link'.")

        links = df["Application link"].dropna().tolist()  # Get all non-empty links

        if not links:
            return {"status": "No links found in the Excel file."}

        # Open each link in the web browser
        for link in links:
            print(f"Opening: {link}")
            webbrowser.open(link)

        return {"status": "Links opened successfully", "total_links": len(links)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while reading the Excel file: {str(e)}")
