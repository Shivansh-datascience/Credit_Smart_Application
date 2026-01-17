from pymongo import MongoClient
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

# MongoDB Functions
def initialize_Mongodb(mongo_uri):
    """Initialize MongoDB client."""
    try:
        client = MongoClient(mongo_uri)
        client.admin.command('ping')
        logging.info("MongoDB connected successfully")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        return None

def connect_with_database_collections(mongo_client, database_name, collection_name):
    """Connect to MongoDB database and collection."""
    try:
        if mongo_client is None:
            raise Exception("MongoDB client is None")
        
        database = mongo_client[database_name]
        collection = database[collection_name]
        
        logging.info(f"Connected to database: {database_name}, collection: {collection_name}")
        return database, collection
    except Exception as e:
        logging.error(f"Failed to connect to database/collection: {e}")
        return None, None

# Pinecone Functions
def initialize_pinecone(api_key, index_name):
    """Initialize Pinecone index."""
    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        logging.info(f"Pinecone index '{index_name}' initialized")
        return index
    except Exception as e:
        logging.error(f"Failed to initialize Pinecone: {e}")
        return None

def get_embeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """Get HuggingFace embeddings."""
    try:
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        logging.info(f"Embeddings model '{model_name}' loaded")
        return embeddings
    except Exception as e:
        logging.error(f"Failed to load embeddings: {e}")
        return None

def initialize_vector_store(index_name, embeddings, namespace):
    """Initialize Pinecone vector store."""
    try:
        vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            namespace=namespace
        )
        logging.info(f"Vector store initialized for index '{index_name}'")
        return vector_store
    except Exception as e:
        logging.error(f"Failed to initialize vector store: {e}")
        return None

def get_retriever(vector_store, k=3):
    """Get Pinecone retriever."""
    try:
        if vector_store is None:
            raise Exception("Vector store is None")
        
        retriever = vector_store.as_retriever(search_kwargs={"k": k})
        logging.info(f"Retriever initialized with k={k}")
        return retriever
    except Exception as e:
        logging.error(f"Failed to get retriever: {e}")
        return None
