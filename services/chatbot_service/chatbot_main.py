import os
import warnings
warnings.filterwarnings('ignore')
# SET HUGGINGFACE CACHE BEFORE ANY IMPORTS (Hig)
os.environ['HF_HOME'] = r'D:\huggingface_cache'
os.environ['TRANSFORMERS_CACHE'] = r'D:\huggingface_cache'
os.environ['HF_DATASETS_CACHE'] = r'D:\huggingface_cache'
import re
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_openai.chat_models import ChatOpenAI
import uvicorn
import uuid
from pydantic import BaseModel
import logging
from langchain_deepseek.chat_models import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# Import from db_config (no circular imports)
from services.chatbot_service.db_config import (
    initialize_Mongodb,
    connect_with_database_collections,
    initialize_pinecone,
    get_embeddings,
    initialize_vector_store,
    get_retriever
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Environment Variables
pinecone_api_key = os.getenv("pinecone_api_key")
deepseek_api_key = os.getenv("deepseek_api_key")
embedding_model = "intfloat/e5-large"
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
MONGO_DB_DATABASE = os.getenv("MONGO_DB_DATABASE")
MONGO_DB_COLLECTION = os.getenv("MONGO_DB_COLLECTION")
Google_api_key = os.getenv("Google_API_key")
index_name = "credit-policy-index"
namespace = "credit-policy-index-1"

# FastAPI App
app = FastAPI(title="Financial RAG Application")
routers = APIRouter()

# Initialize components
logging.info("Initializing RAG components...")

# Pinecone setup

pc_index = initialize_pinecone(pinecone_api_key, index_name)
embeddings = get_embeddings(embedding_model)
vector_store = initialize_vector_store(index_name, embeddings,namespace)
pinecone_retriever = get_retriever(vector_store, k=3)

# MongoDB setup
mongo_client = initialize_Mongodb(MONGO_DB_URI)
mongo_database, mongo_collection = connect_with_database_collections(
    mongo_client, MONGO_DB_DATABASE, MONGO_DB_COLLECTION
)

# LLAMA model LLM
open_router_url = "https://openrouter.ai/api/v1"
llm_model = ChatOpenAI(
    model="meta-llama/llama-3.3-70b-instruct:free",
    api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    base_url=open_router_url,
    temperature=0.0
)

# Helper function
def format_docs(docs):
    if not docs:
        return ""
    return "\n\n".join(
        doc.page_content for doc in docs
        if doc and doc.page_content
    )
#safe context 
def safe_context(context: str):
    if len(context.strip()) < 200:
        return " The provided context does not contain sufficient information to answer this question."
    return context

# RAG Chain
def RAG_chain():
    """Create RAG Chain using LangChain Expression Language"""
    prompt_template = """You are a helpful and reliable assistant specialized in credit scoring and financial analysis.

Use ONLY the information provided in the Context below to answer the user's question.
Include all relevant details like type, tenure, eligible customers, and purposes. 

Context:
{context}

Question:
{question}

Instructions:
- Base your answer strictly on the provided context.
- Do not use external knowledge.
- If the context does not contain enough information, respond: "The provided context does not contain sufficient information to answer this question."

Answer:
"""
    
    rag_prompt = ChatPromptTemplate.from_template(prompt_template)
    
    rag_chain = (
        {
            "context": pinecone_retriever | format_docs | safe_context ,
            "question": RunnablePassthrough()
        }
        | rag_prompt
        | llm_model
        | StrOutputParser()
    )
    
    return rag_chain
rag_chain = RAG_chain()
def clean_rag_output_dynamic(output: str) -> str:
    """
    Dynamically cleans any RAG output:
    - Strips leading/trailing spaces
    - Normalizes multiple newlines to a single newline
    - Removes redundant spaces, tabs
    - Cleans list-like output automatically
    """
    if not output:
        return ""
    
    # Strip leading/trailing whitespace
    cleaned = output.strip()
    
    # Replace multiple newlines or spaces with a single newline
    cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)  # multiple blank lines -> single newline
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)     # multiple spaces/tabs -> single space
    
    # Clean up numbered or bullet lists dynamically:
    # - removes trailing punctuation like ; , . if it seems unnecessary
    # - preserves the sentence end if it’s a proper sentence.
    def clean_line(line: str) -> str:
        line = line.strip()
        # Remove trailing punctuation if line ends with ; or , but not if ends with .
        if line.endswith(';') or line.endswith(','):
            line = line[:-1].strip()
        return line
    
    lines = [clean_line(l) for l in cleaned.split('\n')]
    
    # Join back into clean output
    return "\n".join(lines)

# API Endpoint with request Schema 
class ChatRequest(BaseModel):
    query: str 

@routers.post('/api/chat')
async def chat(request : ChatRequest):
    """Chat endpoint using RAG system."""
    try:
        if not pinecone_retriever:
            raise HTTPException(status_code=500, detail="Vector Store not initialized")
        
        response = rag_chain.invoke(request.query)
    
        # Clean dynamically
        final_response = clean_rag_output_dynamic(response)
    
        
        # Store in MongoDB
        mongo_result = {
            "_id": str(uuid.uuid4()), #generate an random object id 
            "query": request.query,
            "response": final_response
        }
        mongo_collection.insert_one(mongo_result)
        
        return {"response": response, "query": request.query}
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(routers)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
