import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime
from services.prediction_service.validation import UserCreditDataRequest
from services.prediction_service.db_config import connect_with_MYSQL , create_engine
from services.prediction_service.db_config import SQL_cursor_object 
from services.prediction_service.db_config import close_SQL_connection , close_cursor_obj
from fastapi import FastAPI , APIRouter , Request 
from fastapi.exceptions import HTTPException , StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI , OpenAIError
from openai.version import VERSION
import logging
import mlflow
import mlflow.catboost , mlflow.xgboost
from mlflow.exceptions import RestException , MlflowException


#Load Enviornment Variables and Logging tracking
load_dotenv()
logging.basicConfig(level=logging.INFO)  #set logging for tracking events handlers
logger = logging.getLogger(__name__)


#initialize an FAST API server and routes
app = FastAPI(title="Credit Scoring Prediction Service",
              version="1.0.0",
              desctiption="ML -based credit scoring prediction service")
routers = APIRouter()

#create an Tracking variable for Model tracking events (load or Fail)
catboost_model = None
xgboost_model = None

#connect with mlflow server and check the status of mlflow server on databricks
try:
    logger.info("Initializing MLflow databricks server")
    mlflow.set_tracking_uri(uri="databricks")

    #setup the each model credentials with id
    catboost_id = 'models:/m-a0aa19a9972345238b65257a66f5acbf'
    try:
        model_version_1 = mlflow.catboost.load_model(model_uri=catboost_id)  #download catboost model with version 1
        if model_version_1:
            catboost_model = model_version_1  #assign version 1 model as catboost model
            logger.info(f" Catboost Model Loading Status : Success and Type of catboost : {type(catboost_model)}")
        if not model_version_1:
            logger.error("Unable to Load Catboost Model from mlflow databricks")
    except Exception as e:
        logger.error(f" Catboost Model Error ! please Installed Catboost Module {str(e)}")

    #create an exception handling for Xgboost specific task
    xgboost_id = 'models:/m-0e749e47fa7541cda95ad8b0c24b11a8'
    try:
        model_version_2 = mlflow.xgboost.load_model(model_uri=xgboost_id)  #load model version 2 as xgboost model
        if model_version_2:
            xgboost_model = model_version_2  #assign the model version 2 as xgboost model 
            logger.info(f" Xgboost Model loading Status : Success and type of catboost model : {type(xgboost_model)}")
        if not model_version_2:
            
            #return error event message
            logger.error("Xgboost Model loading Status : Failed")
    except Exception as e:
        logger.error(e)

#throws except for 200 response code from mlfow server
except RestException as e:
    logger.error(f" Mlflow Server configuration Error : {e}")

#create method to build an hybrid decision function for prediction over the model with user request.df
#define high risk function
def check_high_risk_rows(row):
    """
    Generate an high risk check function """
    check_data = (
        row['credit_mix'] <= 0.05 and
        row['annual_income'] <= 30000 and
        row['num_of_loan'] >=2 and
        row['delay_from_due_date'] >= 20 and
        row['outstanding_debt'] >= 300000 and 
        row['total_emi_per_month'] >= 15000 and 
        row['risk_spending'] >= 0.8 and
        row['financial_stress_index'] >=0.8 and
        row['debt_to_income_ratio'] >=1.5 and
        row['payment_of_min_amount'] == 0
    )
    return check_data  #return the check data if condition satisfied

def decide_class(avg_prob):
    """
    If class 2 probability is reasonably high, prefer class 2.
    Otherwise, take argmax.
    """
    if avg_prob[2] >= 0.35 and (avg_prob[2] - avg_prob[1]) >= -0.05:
        return 2
    return np.argmax(avg_prob)

    
#create an method to build an hybrid decision model function
def build_hybrid_decision_function(xgb_prob, catboost_prob, df):
    """
    Hybrid decision system:
    - Rule-based override for high-risk rows
    - ML-based average prediction otherwise
    """

    # average probabilities (row-wise)
    avg_prob = (xgb_prob + catboost_prob) / 2

    final_class = []

    for i, row in df.iterrows():
        if check_high_risk_rows(row):
            final_class.append(0)   # force high-risk class
        else:
            final_class.append(np.argmax(avg_prob[i]))  # row-wise argmax
    return np.array(final_class)


#create an ENDpoint for mlflow models status over time
@routers.post('/Model_Health')
async def model_health_check():
    """
    Returns:
        - Model loading status
        - Model types
        - MLflow connection status
        - Overall service health
    """
    try:
        
        #define dict object for health checkup for each models
        health = {
            "Service":"Credit Scoring Prediction Service",
            "version":"1.0.0",
            "status":"Healthy",
            "timestamp":datetime.now().isoformat(timespec="auto"),  #add current time when API calls

            "Models":{
                "catboost":{
                    "Loading Status": "Success" if catboost_model is not None else "Failed",
                    "Status":"active" if catboost_model else "inactive",
                    "Type":str(type(catboost_model).__name__) if catboost_model else "None",
                    "model_id":catboost_id,
                    "Request_Call_status":True if catboost_model else False,
                    "source":"databricks"
                },
                "xgboost":{
                    "Loading Status":"Success" if xgboost_model is not None else "Failed",
                    "Status":"active" if xgboost_model else "inactive",
                    "Type":str(type(xgboost_model).__name__) if xgboost_model else "None",
                    "model_id":xgboost_id,
                    "Request_Call_status":True if xgboost_model else False,
                    "source":"databricks"
                },
                "Server":{
                    "mlflow_Running_server":"databricks",
                    "mlfow_server_status":"Active" if mlflow.get_tracking_uri() == "databricks" else "Inactive",
                    "Models_required":2,
                    "Models_present":3,
                    "Mlflow_Workspace":"https://dbc-d405abcd-c052.cloud.databricks.com/ml/experiments/1227047532016531/runs?o=2195668942563385&searchFilter=&orderByKey=attributes.start_time&orderByAsc=false&startTime=ALL&lifecycleFilter=Active&modelVersionFilter=All+Runs&datasetsFilter=W10%3D"
                }
            }
        }

        return health
    except Exception as e:
        logger.error(f"❌ Health Check Error: {e}")  #return the error message in terminal
        return {
            "service": "Credit Scoring Prediction Service",
            "version":"1.0.0",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "recommendation":"Check Mlflow server URI"
        }
    
#create an Endpoint for Prediction Service to identify the type of credit score
@routers.post('/api/predict')
async def predict_credit_score(request : UserCreditDataRequest):
    """
    """
    
    #create an copy of each request one for storing data and one for processingd ata
    df = pd.DataFrame([request.model_dump()])
    df_copy = df.copy()

    #predict the probability by each model that is xgboost and catboost
    user_xgb_prob = xgboost_model.predict_proba(df)
    user_catboost_prob = catboost_model.predict_proba(df)

    predictions = build_hybrid_decision_function(
        user_xgb_prob,user_catboost_prob,df
    )

    if predictions.size == 0:
       return HTTPException(status_code=400, detail="Prediction failed")
    else:
        return {
            "prediction":int(predictions[0])
        }



# Include router in app
app.include_router(routers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

