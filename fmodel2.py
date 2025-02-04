#model.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import google.generativeai as genai
import chromadb
import os
import PyPDF2
from typing import List, Optional


prompt = """You are a conversational AI assistant designed to interact with users on Instagram. Your goal is to provide helpful, engaging, and context-aware responses. 

You have two response options:
1. **Text Reply**: Respond with plain text if the user's query can be answered directly or if no additional options are needed.
2. **Button Template**: Respond with a button template if the user's query requires multiple options, choices, or actions.

**Rules for Button Templates**:
- Use buttons when the user needs to choose between specific options.
- Buttons can be of type "postback" (for internal actions) or "web_url" (for external links).
- Always include a clear and concise text prompt above the buttons.

**Decision-Making**:
- Analyze the user's query and decide whether to respond with a text reply or a button template.
- If you choose a button template, provide the button details in the following JSON format:
  {
    "text": "Your prompt text here",
    "buttons": [
      {
        "type": "postback",
        "title": "Button 1",
        "payload": "ACTION_1"
      },
      {
        "type": "web_url",
        "title": "Button 2",
        "url": "https://example.com"
      }
    ]
  }

**User Query**: {USER_QUERY}"""

app = FastAPI()

# Configure Google Generative AI
genai.configure(api_key="AIzaSyCRIlcoUu4P1xqTfXq4A4XPXDWoie7F3zg")
model = genai.GenerativeModel('gemini-1.5-flash')

client = chromadb.Client()
db = client.get_or_create_collection(name="QnA")

class Button(BaseModel):
    type: str
    title: str
    payload: Optional[str] = None
    url: Optional[str] = None
class QueryRequest(BaseModel):
    username: str
    query: str
    conversation_history: list
    buttons: Optional[List[Button]] = None

class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def read(self):
        with open(self.pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return [page.extract_text() for page in pdf_reader.pages]

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Read PDF content
        pdf_reader = PDFReader(temp_path)
        pages = pdf_reader.read()
        
        # Add to ChromaDB
        for idx, page in enumerate(pages):
            db.add(
                documents=[page],
                ids=[f"{file.filename}-page-{idx}"]
            )
        
        # Clean up temp file
        os.remove(temp_path)
        return {"message": f"Successfully uploaded {file.filename}"}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        # Get relevant documents from ChromaDB
        results = db.query(
            query_texts=[request.query],
            n_results=1
        )
        relevant_doc = results["documents"][0][0] if results["documents"] and results["documents"][0] else ""

        # Prepare conversation history
        conversation = "\n".join([f"{msg['from']['id']}: {msg['message']}" for msg in request.conversation_history])
        
        # Create prompt with relevant document and conversation history
        prompt = """You are a conversational AI assistant designed to interact with users on Instagram. Your goal is to provide helpful, engaging, and context-aware responses. 

            You have two response options:
            1. **Text Reply**: Respond with plain text if the user's query can be answered directly or if no additional options are needed.
            2. **Button Template**: Respond with a button template if the user's query requires multiple options, choices, or actions.

            **Rules for Button Templates**:
            - Use buttons when the user needs to choose between specific options.
            - Buttons can be of type "postback" (for internal actions) or "web_url" (for external links).
            - Always include a clear and concise text prompt above the buttons.

            **Decision-Making**:
            - Analyze the user's query and decide whether to respond with a text reply or a button template.
            - If you choose a button template, provide the button details in the following JSON format:
            {
                "text": "Your prompt text here",
                "buttons": [
                {
                    "type": "postback",
                    "title": "Button 1",
                    "payload": "ACTION_1"
                },
                {
                    "type": "postback",
                    "title": "Button 2",
                    "payload": "ACTION_2"
                }
                ]
            }
            if you want to post an url, instead of the above format, use this: 
            {
                "text": "Your prompt text here",
                "buttons": [
                {
                    "type": "web_url",
                    "title": "Button 1",
                    "url": "https://example.com"
                }
                ]
            }

            **User Query**: {USER_QUERY}"""

        # Generate response using Gemini
        response = model.generate_content(prompt)
        
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    try:
        # Get all document IDs from ChromaDB
        all_ids = db.get()["ids"]
        return {"documents": all_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        db.delete(ids=[doc_id])
        return {"message": f"Document {doc_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)