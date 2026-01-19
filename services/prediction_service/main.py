from openai import OpenAI
from fastapi import FastAPI , Request , HTTPException , APIRouter
from services.prediction_service.db_config import connect_with_MYSQL 
from services.prediction_service.db_config import close_SQL_connection , close_cursor_obj
from services.prediction_service.db_config import SQLconnection_with_string
from services.prediction_service.validation import UserCreditDataRequest
from fastapi.exceptions import HTTPException
from fastapi.openapi.models import APIKey
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import mlflow
import mlflow.catboost
import mlflow.sklearn , mlflow.xgboost
from mlflow.pyfunc import load_model


#load environment variable for Database connection 
