from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Configure Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

class QueryRequest(BaseModel):
    username: str
    query: str
    conversation_history: list
@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        # Prepare the conversation history for the model
        conversation = "\n".join([f"{msg['from']['id']}: {msg['message']}" for msg in request.conversation_history])
        prompt = f"Conversation History:\n{conversation}\n\nUser: {request.query}\nAI:"

        # Generate response using Gemini 2.0 Flash
        response = model.generate_content(prompt)

        return {"response": response.text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)