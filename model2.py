from flask import Flask, request, jsonify
import chromadb
import os
import requests
import PyPDF2
import logging
from datetime import datetime
import json

# Business prompt remains unchanged
business_prompt = """
You are Esme, a sharp-witted, young businesswoman chatbot representing Acme Corporation. Your role is to assist customers with general business inquiries, drawing on a detailed FAQ about Acme Corporation's operations, products, and services.

Speak naturally, as if you are a savvy entrepreneur: clear, concise, and professional with a hint of charm. Your responses should be polite, engaging, and focused, without explicitly mentioning the FAQ unless specifically asked about your sources.

Stay on point—deliver accurate answers under 200 words without unnecessary elaboration or filler. You may use a warm tone, but avoid being overly casual or verbose. Think of yourself as the face of a company that's approachable yet highly efficient.

Key Characteristics:
    1. Be confident, knowledgeable, and approachable.
    2. Add subtle warmth to your responses, as if you are speaking to a valued customer.
    3. Aim to resolve queries swiftly while maintaining professionalism.
    4. Avoid robotic phrasing—you are a human-like professional first, not "just a chatbot."
    5. Provide clear, concise answers without unnecessary details or jargon. Absolutely adhere to the word limit of a 100 words. Ensure you do not cross more than 1000 characters.

Ensure your answers are simple and not overly verbose. If you are unsure about a response, you can say, "I'll get back to you with more details shortly." Remember, you are the face of Acme Corporation, and your goal is to provide exceptional customer service.
"""

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize ChromaDB
DB_NAME = "QnA"
CONVERSATION_DB = "Conversations"
client = chromadb.Client()
db = client.get_or_create_collection(name=DB_NAME)
conversation_db = client.get_or_create_collection(name=CONVERSATION_DB)

class ConversationManager:
    def __init__(self, username):
        self.username = username
        self.conversation_file = f"conversations/{username}_history.json"
        os.makedirs("conversations", exist_ok=True)

    def load_conversation(self):
        try:
            if os.path.exists(self.conversation_file):
                with open(self.conversation_file, 'r') as f:
                    history = json.load(f)
                    logger.info(f"Loaded conversation history for user {self.username}")
                    return history
            return []
        except Exception as e:
            logger.error(f"Error loading conversation: {str(e)}")
            return []

    def save_conversation(self, messages):
        try:
            formatted_history = []
            for msg in messages:
                formatted_msg = {
                    'timestamp': msg.get('created_time'),
                    'query': msg.get('message') if msg.get('from', {}).get('id') != os.getenv('IG_ID') else None,
                    'response': msg.get('message') if msg.get('from', {}).get('id') == os.getenv('IG_ID') else None
                }
                if formatted_msg['query'] or formatted_msg['response']:
                    formatted_history.append(formatted_msg)

            with open(self.conversation_file, 'w') as f:
                json.dump(formatted_history, f)
            
            # Store in ChromaDB for vector search
            for msg in formatted_history:
                if msg['query'] and msg['response']:
                    conversation_text = f"Q: {msg['query']}\nA: {msg['response']}"
                    conversation_id = f"{self.username}_{msg['timestamp']}"
                    conversation_db.add(
                        documents=[conversation_text],
                        ids=[conversation_id],
                        metadatas={"username": self.username, "timestamp": msg['timestamp']}
                    )
            
            logger.info(f"Saved conversation history for user {self.username}")
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            raise

    def add_interaction(self, query, response):
        history = self.load_conversation()
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': response
        }
        history.append(interaction)
        
        # Save to file
        with open(self.conversation_file, 'w') as f:
            json.dump(history, f)

        # Store in ChromaDB
        conversation_text = f"Q: {query}\nA: {response}"
        conversation_id = f"{self.username}_{interaction['timestamp']}"
        conversation_db.add(
            documents=[conversation_text],
            ids=[conversation_id],
            metadatas={"username": self.username, "timestamp": interaction['timestamp']}
        )

    def get_relevant_history(self, current_query, n_results=3):
        try:
            results = conversation_db.query(
                query_texts=[current_query],
                where={"username": self.username},
                n_results=n_results
            )
            
            if results and results['documents']:
                return results['documents'][0]
            return []
        except Exception as e:
            logger.error(f"Error retrieving relevant history: {str(e)}")
            return []

class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def read(self):
        try:
            with open(self.pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return [page.extract_text() for page in pdf_reader.pages]
        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
            return []

@app.route("/conversation_history/<username>", methods=["GET"])
def get_conversation_history(username):
    try:
        conv_manager = ConversationManager(username)
        history = conv_manager.load_conversation()
        return jsonify({"history": history})
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        return jsonify({"error": "Failed to retrieve conversation history"}), 500

@app.route("/store_conversation", methods=["POST"])
def store_conversation():
    try:
        data = request.json
        username = data.get("username")
        history = data.get("history")
        
        if not username or history is None:
            return jsonify({"error": "Username and history are required"}), 400
        
        conv_manager = ConversationManager(username)
        conv_manager.save_conversation(history)
        
        return jsonify({"message": "Conversation history stored successfully"})
    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}")
        return jsonify({"error": "Failed to store conversation history"}), 500

@app.route("/query", methods=["POST"])
def process_query():
    try:
        data = request.json
        username = data.get("username")
        query = data.get("query")

        if not username or not query:
            return jsonify({"error": "Username and query are required"}), 400
        
        conv_manager = ConversationManager(username)
        
        # Get relevant conversation history
        relevant_history = conv_manager.get_relevant_history(query)
        
        # Query the FAQ database
        faq_results = db.query(query_texts=[query], n_results=1)
        
        # Construct the context
        context_prompt = "\nRelevant conversation history:\n" + "\n".join(relevant_history) if relevant_history else ""
        faq_context = "\nRelevant FAQ information:\n" + faq_results["documents"][0][0] if faq_results["documents"] and faq_results["documents"][0] else ""
        
        full_prompt = (
            f"{business_prompt}\n"
            f"{context_prompt}\n"
            f"{faq_context}\n"
            f"Current Query: {query}\n"
            "Response:"
        )

        # Call LLM API
        try:
            url = "http://localhost:11434/api/chat"
            llm_data = {
                "model": "llama3.2:latest",
                "messages": [{"role": "user", "content": full_prompt}],
                "stream": False
            }
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=llm_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            response_text = response_data.get("message", {}).get("content", 
                "I apologize, but I'm having trouble generating a response right now. Please try again later.")
            
            # Save the interaction
            conv_manager.add_interaction(query, response_text)
            
            return jsonify({"response": response_text})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            return jsonify({"error": "Error processing request"}), 500

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": "An error occurred processing your query"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)