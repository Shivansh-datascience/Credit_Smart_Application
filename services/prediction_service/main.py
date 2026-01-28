import os
from dotenv import load_dotenv
import pandas as pd
import requests
import numpy as np
from datetime import datetime
from services.prediction_service.validation import UserCreditDataRequest , RecommendationRequest
from services.prediction_service.db_config import connect_with_MYSQL , create_engine
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

#load SQL credentials from environment Variables
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQl_DATABASE")
MYSQL_TABLE = os.getenv("MYSQL_TABLE")
MYSQL_SERVICE_ID = os.getenv("MYSQL_SERVICE_ID")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

#recommendation URL 
llama3_url = "https://openrouter.ai/api/v1/chat/completions"

#check for request status code 
target_code = 200  #assign target code  
actual_code = ''  #return actual http status code

#check if target code is equal to request module status code 
if requests.status_codes == target_code:

    actual_code = target_code   #assign target code as actual code 
    logger.info("Open router LLAMA3 URL Status : True")
else:
    actual_code = None   #store None if not connected to server
    logger.info("Open router LLAMA3 URL Status : False")

#call the database methods to connect with MYSQL connection
mysql_connection = connect_with_MYSQL(
    sql_user=MYSQL_USERNAME,
    sql_password=MYSQL_PASSWORD,
    sql_database=MYSQL_DATABASE,
    sql_port=int(MYSQL_PORT),
    sql_host=MYSQL_HOST
)


#check for mysql connection if successfully connected
if mysql_connection is not None:

    #connect and initialize cursor object
    mysql_cursor_obj = mysql_connection.cursor()
    
if mysql_connection is None:
    logger.info("Cursor object not initialized ! Check database connection")

#initialize an FAST API server and routes
app = FastAPI(title="Credit Scoring Prediction Service",
              version="1.0.0",
              desctiption="ML -based credit scoring prediction service")
app.state.session = 0  #define an static session to count occurence of request for Prediction service
app.state.recommendation_session = 0   #define an static session for recommendation request
max_retry_limit = 5    #store an maximum retry limit 
window_limit = 60   #set 60 seconds time limit for request user 

#define state session
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
    # Only force Class 2 if probability is high enough
    if avg_prob[2] >= 0.40 and (avg_prob[2] - avg_prob[1]) >= -0.05:
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
            final_class.append(decide_class(avg_prob[i])) # row-wise argmax to get class 2 if not enough fallback to class 1 logic
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
    Predict customer credit score and risk category using ML models.
    
    Returns:
        dict: Prediction with Category and Risk Segment
    """
    
    #check for upcoming Client request from server
    if request:
        app.state.session += 1  #apply increment based on session state for FAST API internal architecture

        if app.state.session >= max_retry_limit:
            app.state.session = 0   #set the request to zero 

            #return startette HTTP exception error on prediction server
            return StarletteHTTPException(
                status_code=429,
                detail="Prediction Limit request completed",
                headers="Retry AFter 60 seconds"
            )
        
    #create an copy of each request one for storing data and one for processing data
    df = pd.DataFrame([request.model_dump()])
    df_copy = df.copy()

    #predict the probability by each model that is xgboost and catboost
    user_xgb_prob = xgboost_model.predict_proba(df)
    user_catboost_prob = catboost_model.predict_proba(df)

    predictions = build_hybrid_decision_function(
        user_xgb_prob,user_catboost_prob,df
    )

    #assign the labels as based on prediction category
    credit_score_category = ""  #create an tracking variable 
    risk_type_category = ""

    #check the predictions classess 
    if predictions[0] == 2:
        credit_score_category = "Standard Case Category"
        risk_type_category = "Medium Risk "
    elif predictions[0] == 1:
        credit_score_category = "Good Case Category"
        risk_type_category = "Low Risk"
    else:
        credit_score_category = "Poor Case Category"
        risk_type_category = "High Risk"

       
    if predictions.size == 0:
       return HTTPException(status_code=400, detail="Prediction failed")
    else:

        #store the data into database
        query = f"""
        insert into {MYSQL_TABLE} (
            credit_mix, annual_income,
            num_bank_accounts, num_credit_card, num_of_loan,
            interest_rate, delay_from_due_date,
            changed_credit_limit, outstanding_debt,
            total_emi_per_month,
            risk_spending, financial_stress_index, debt_to_income_ratio,
            payment_of_min_amount, credit_score_category, risk_category
        ) 
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        #store data into MYSQL database
        mysql_cursor_obj.execute(query,(
            request.credit_mix,request.annual_income,
            request.num_bank_accounts,request.num_credit_card,
            request.num_of_loan,request.interest_rate,request.delay_from_due_date,
            request.changed_credit_limit,request.outstanding_debt,request.total_emi_per_month,
            request.risk_spending,request.financial_stress_index,request.debt_to_income_ratio,
            request.payment_of_min_amount,credit_score_category,risk_type_category
        ))

        #commit the cursor object
        mysql_connection.commit()

        #close connection status for cursor object and mysql connection
        close_cursor_obj(mysql_cursor_obj)

        close_SQL_connection(mysql_connection)

        #return JSON response to user with Category assign and Risk Category

        return {
            "Category":credit_score_category,
            "Risk Segment":risk_type_category   
        }

#create an post HTTP request method for Recommendation 
@routers.post("/api/credit-risk-explanation")
async def credit_risk_explaination(request : RecommendationRequest):

    """
    Generate a human-readable credit risk explanation and financial recommendations.

    This endpoint accepts a validated credit profile along with the final
    credit risk decision produced by a predictive model. It uses a
    language model to generate:
    - An explanation of why the user falls into the given risk category
    - Actionable recommendations to maintain or improve credit health
    - Cautionary points highlighting potential future risks

    The endpoint does not perform risk prediction. It only provides
    explainability and advisory insights based on the supplied model output.

    :param request: Structured input containing the user's credit profile
                    and the model-generated risk category and segment.
    :type request: RecommendationRequest

    :return: A structured explanation, recommendations, and caution points
             validated against the CreditRecommendation schema.
    :rtype: CreditRecommendation
    """

    #add Rate Limiting for each request for user
    if request.user_request:

        #add the session increment in recommendation session created
        app.state.recommendation_session += 1

        if app.state.recommendation_session >= max_retry_limit:

            #assign the session limit as zero if retry limit exceed over defined request
            app.state.recommendation_session = 0

            #return the starlete http exception over status code as 429
            return StarletteHTTPException(
                status_code=429,
                detail="Request Limit Exceeds ! Try after 60 seconds or 1 minute"
            )
        
    try:
         
        #create an client session for openai llama3b model for explaination
        llama3b_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPEN_ROUTER_API_KEY
        )

        model_name = "meta-llama/llama-3.3-70b-instruct:free"
        #create an json prompt for system message and user role message 
        recommendation_message = [
            {
                "role":"system",
                "content": "You are a financial advisor AI with domain knowledge in credit risk, personal finance, and debt management. A user will provide their credit and financial information in normal text, such as: income, number of loans, delays in payment, spending habits, and other relevant information.\n\nYour task is to:\n\n1. Identify the user's credit risk level: High, Medium, or Low.\n2. Analyze their financial profile using domain knowledge.\n3. Highlight strengths in the user's financial behavior.\n4. Identify areas needing improvement, focusing on:\n   - Reducing outstanding debt\n   - Avoiding delays in payments\n   - Managing risk spending\n   - Optimizing monthly EMI obligations\n   - Improving credit mix\n   - Maintaining healthy debt-to-income ratio\n5. Provide personalized, actionable recommendations based on their risk level:\n   - High risk → urgent corrective actions and preventive steps\n   - Medium risk → moderate actions and tips to prevent risk escalation\n   - Low risk → suggestions to maintain or improve financial health\n6. Optionally, provide additional advice:\n   - Reviewing interest rates\n   - Consolidating loans\n   - Automating payments\n   - Building emergency savings\n   - Improving financial stress management\n\nColumns to focus on for analysis (if mentioned or implied by user text):\n- credit_mix\n- annual_income\n- num_bank_accounts\n- num_credit_card\n- interest_rate\n- num_of_loan\n- delay_from_due_date\n- changed_credit_limit\n- outstanding_debt\n- total_emi_per_month\n- risk_spending\n- financial_stress_index\n- debt_to_income_ratio\n- payment_of_min_amount\n\nOutput Format (structured for clarity):\n\nCredit Risk Level: {High / Medium / Low}\n\nStrengths:\n- {Highlight user's financial strengths based on columns/domain knowledge}\n\nAreas to Improve:\n- {List key areas for improvement based on columns/domain knowledge}\n\nRecommendations:\n1. {Actionable recommendation 1}\n2. {Actionable recommendation 2}\n3. {Actionable recommendation 3}\n...\n\nAdditional Advice:\n- {Optional extra suggestions or domain knowledge insights}\n\nImportant: Use normal text from the user to extract values, infer patterns, and provide clear advice. Make it actionable, easy to understand, and personalized."
            },
            {
                "role":"user",
                "content":request.user_request   #user actual question 
            }
        ]

        #create an chain for recommendation
        completion = llama3b_client.chat.completions.create(
            model=model_name,
            messages=recommendation_message,
            max_tokens=500      #return the maximum token request limit as 500 
        )

        #create an object to store the recommendation result
        result = completion.choices[0].message.content  

        #return json message if result is not empty
        if result:

            return {
                "Recommendation_Result":result
            }
        else:
            raise HTTPException(status_code=500, detail="Empty LLM response")
        
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Recommendation generation failed: {str(e)}"
        )


# Include router in app
app.include_router(routers)

#add middleware for FAST API application

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)



