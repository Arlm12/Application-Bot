import os
import fitz  # PyMuPDF
import openai
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob
from fastapi import APIRouter, UploadFile, File, HTTPException


router = APIRouter()
#client = openai.OpenAI(api_key=api_key)

def extract_full_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = []

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    if line_text.strip():
                        full_text.append(line_text.strip())

    return "\n".join(full_text)


def ask_gpt_to_structure_resume(raw_text):

    prompt = f"""You are a resume parser. Here's the unstructured resume text extracted from a PDF: {raw_text} 
    You extract it into a structured JSON. 
    - Include all the details. 
    - Make sure the associations are correct: dates should go with roles, skills should not include random words, etc."""

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}

    )

    parsed_resume = json.loads(response.choices[0].message.content.strip())

    print(f"Structured Resume:\n{parsed_resume}")
    return parsed_resume


@router.get("/parse-resume/")
def parse_resume():
    print("Works!")
    resume_path = "data/resume.pdf"
    resume_text = extract_full_text(resume_path)
    structured = ask_gpt_to_structure_resume(resume_text)

    os.makedirs("data", exist_ok=True)

    json_path = "data/structured_resume.json"
    if os.path.exists(json_path):
        os.remove(json_path)
        print(f"Deleted old file: {json_path}")

    # Save the new structured resume as JSON
    with open(json_path, "w") as f:
        json.dump(structured, f, indent=2)

    return structured