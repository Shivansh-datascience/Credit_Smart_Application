from services.chatbot_service.chatbot_validation import Chatbot_Wrapper
from services.chatbot_service.db_config import initialize_Mongodb , connect_with_database_collections
from dotenv import load_dotenv
import os

load_dotenv()


#fetch Pinecone API key and Deepseek API from environment Variables
pinecone_api_key = os.getenv("pinecone_api_key")
deepseek_api_key = os.getenv("deepseek_api_key")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
MONGO_DB_DATABASE = os.getenv("MONGO_DB_DATABASE")
MONGO_DB_COLLECTION = os.getenv("MONGO_DB_COLLECTION")
MONGODB_USER = os.getenv("MONGODB_USER")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
index_name = "credit-policy-index"
pinecone_host_server = "https://credit-policy-index-wnvzyhf.svc.aped-4627-b74a.pinecone.io"

wrapper = Chatbot_Wrapper(pinecone_api_key,deepseek_api_key,embedding_model,index_name,pinecone_host_server)

pc_conn , result = wrapper.connect_with_pinecone_server()
pc_index , index_result = wrapper.connect_with_pinecone_index(pc_conn,index_name)
embedder = wrapper.Hugging_Face_embedding_model()
print(f" Pinecone Connection Result : {result}")
print(f" Pinecone Index database Result: {index_result}")
print(f" Hugging Face Embedding Model : {embedder}")

#test methods for Database
# Test MongoDB connection
mongo_client = initialize_Mongodb(MONGO_DB_URI)

if mongo_client is None:
    print("ERROR: Failed to initialize MongoDB client")
else:
    mongo_db, mongo_collection = connect_with_database_collections(
        mongo_client, MONGO_DB_DATABASE, MONGO_DB_COLLECTION
    )
    
    if mongo_db is None or mongo_collection is None:
        print("ERROR: Failed to connect to database/collection")
    else:
        print(f"MONGO DB client: {mongo_client}")
        print(f"MONGO DB database: {mongo_db}")
        print(f"Mongo DB collections: {mongo_collection}")
