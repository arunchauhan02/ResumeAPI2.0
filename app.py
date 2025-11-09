import os
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.prompts import PromptTemplate
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    allow_creddentials=True,
    allow_methods=["*"]
    allow_headers=["*"]
)

# Configure Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

PROMPT_TEMPLATE = """
You are an expert resume parser. Given the resume text, extract the following fields and return a single valid JSON object:

{
  "Name": "...",
  "Email": "...",
  "Phone": "...",
  "LinkedIn": "...",
  "Skills": [...],
  "Education": [...],
  "Experience": [...],
  "Projects": [...],
  "Certifications": [...],
  "Languages": [...]
}

Rules:
- If a field cannot be found, set its value to "No idea".
- Return ONLY valid JSON (no extra commentary).
- Keep lists as arrays, and keep Experience/Projects as arrays of short strings.

Resume text:
{text}
"""

prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["text"])

def load_resume(file_path: str, filename: str):
    if filename.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif filename.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
    elif filename.endswith(".txt"):
        loader = TextLoader(file_path)
    else:
        return None
    return loader.load()

@app.post("/parse-resume/")
async def parse_resume(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    docs = load_resume(temp_path, file.filename)
    if not docs:
        return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

    full_text = "\n\n".join([d.page_content for d in docs])
    formatted_prompt = prompt.format(text=full_text)

    response = llm.invoke(formatted_prompt)
    try:
        parsed_json = json.loads(response.content)
        return parsed_json
    except json.JSONDecodeError:
        return {"raw_response": response.content}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
