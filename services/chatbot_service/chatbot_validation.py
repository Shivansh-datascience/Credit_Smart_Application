#create an class wrapper for loading Pinecone vector database with deepseek model
import os
import logging
import pinecone
from pinecone import Pinecone , PineconeException , PineconeApiException
from langchain_pinecone.vectorstores import PineconeVectorStore
from langchain_huggingface.embeddings import HuggingFaceEmbeddings


#create an class wrapper for loading Pinecone vector database with deepseek model
class Chatbot_Wrapper:
    def __init__(
            self,pinecone_api_key,deepseek_api_key,embedding_model,index_name,pinecone_host_server,pinecone_namespace):

        """ Create an Abstraction Layer for Passing API with connection to required Server"""
        self.pinecone_api_key = pinecone_api_key,
        self.deepseek_api_key = deepseek_api_key,
        self.embedding_model = embedding_model
        self.pinecone_host = pinecone_host_server
        self.index = index_name
        self.namespace = pinecone_namespace
    
    def connect_with_pinecone_server(self):

        """ Connect with Pinecone Server"""
        try:
            pc = Pinecone(api_key = self.pinecone_api_key , environment = "us-east-1")  #connect with Pinecone server
            #check if connection is True or False with result 
            if pc:

                #return Connection object with Status Result as True
                return pc , True 
            else:
                return False  #return status results as False if connection is not initialized
        except PineconeApiKeyError as api_error:
            raise ValueError(str(api_error))  #raise api key authentication error
        
        #function for making connection to index name
    def connect_with_pinecone_index(self,pc_con,index_name):

        """ Connect with Pinecone Index for Database"""
        try:

            #create an connection object with Index name
            pc_index = pc_con.Index(index_name,host=self.pinecone_host)
            if pc_index is not None:
                return pc_index , True   #return index connection obj with Status result
            else:
                return False     #return boolean result if index not connected to pinecone server
        except PineconeException as exception_error:
            raise ValueError(str(exception_error))
    
    #create an function to return Hugging face embedding
    def Hugging_Face_embedding_model(self):

        """ Return embedding model combined as Hugging Face"""
        embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model)
        return embedding_model

    #create an vector store retriever with namespace , index name , embedding model
    def initialize_vector_store(self):

        """
        Docstring for initialize_vector_store
        
        :param self: Description
        """
        try:
            embedding_model = HuggingFaceEmbeddings()  #call hugging face embedding model

            #create an vector store for pinecone
            vector_store = PineconeVectorStore(
                index = self.index,
                embedding = embedding_model,
                namespace = self.namespace
            )
            return vector_store.as_retriever(search_kwargs={"k": 3})  #return vector store retriever object
        except Exception as e:
            logging.error(f"Failed to initialize vector store: {e}")
            return None
    
