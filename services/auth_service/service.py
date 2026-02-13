import yaml
from smtplib import SMTP 
import requests
import logging
import hashlib
from email.message import  EmailMessage
from fastapi import FastAPI, HTTPException, Request, APIRouter
from auth.OTP_generator import connect_redis_server, generate_OTP_authentication
from auth.OTP_session import store_otp_in_redis, get_otp_from_redis, verify_user_otp_number
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from .validation import OTP_Validation_Wrapper , OTP_Verification_Wrapper  # Fixed import
from .validation import UserRegisteration , UserLogin  #import for User registeration and login 
from .validation import UpdateUsername , UpdatePassword
from dotenv import load_dotenv
import os
import uvicorn
import pymysql

load_dotenv()

#load API key from environment variable s
fast2_sms_api_key = os.getenv("fast2_sms_api_key")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQl_DATABASE")
MYSQL_TABLE = os.getenv("MYSQL_TABLE_1")
MYSQL_SERVICE_ID = os.getenv("MYSQL_SERVICE_ID")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#connect with mysql database
connection = pymysql.connect(user=MYSQL_USERNAME,
                             password=MYSQL_PASSWORD,
                             database=MYSQL_DATABASE,
                             port=int(MYSQL_PORT),
                             host=MYSQL_HOST)

if connection !=None:

    logging.info("Connection status for MYSQL : True")
connection_cursor_obj = connection.cursor()  #create an cursor object to execute dynamic SQL queries

# Load YAML file (fixed relative path)
yaml_file_path = r"D:\credit_scoring_project\services\auth_service\auth_config.yaml"
with open(yaml_file_path, 'r') as yaml_content:
    config_data = yaml.safe_load(yaml_content)

# Create FastAPI app
app = FastAPI(title="OTP Authentication",version="1.0.0",description="OTP authentication for Credit smart Application")

#add session state for Rate Limiting 
app.state.otp_session = 0

#add the maximum retry limit
Max_retry_limit = 5


#allow this api access to frontend 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
routers = APIRouter()

@routers.post("/auth/Generate_OTP")
async def generate_otp(request: OTP_Validation_Wrapper):
    """
    Generate OTP for the given Email Address.
    """

    #check the request for rate limiting 
    if request:
        
        #add the session increment for each request
        app.state.otp_session += 1

        if app.state.otp_session >= Max_retry_limit:

            #assign the session as zero if condition verified
            app.state.otp_session = 0

            #return status code 429 for two many request 
            return HTTPException(
                status_code=429,detail="Too many request in OTP service Server"
            )

    try:
        """ Request Email ID from user Though Client Session """
        email_id = request.email_address

        global generated_otp  #initialized OTP as global key

        #generate otp by calling generate otp authentication with parameters as email address
        secret_key, generated_otp = generate_OTP_authentication(email_address=email_id)
        otp_value = generated_otp.now()  #return current otp 

        
        # Connect to Redis (fixed port)
        redis_conn = connect_redis_server(
            redis_host=config_data['redis']['host'],
            redis_port=config_data['redis']['port']  # Fixed
        )
        
        # Store OTP in Redis
        store_otp_in_redis(email_id, secret_key, otp_value, redis_conn)
        
        # Send OTP via Email Service
        #create an template for send email message to reciever

        contents = f"""Hello,

        Welcome to Credit Smart 👋

        To proceed with your secure login, please use the One-Time Password (OTP) below:

        🔐 Your OTP: {otp_value}

        This OTP is valid for 5 minutes only.
        Please do not share this OTP with anyone for security reasons.

        If you did not request this verification, please ignore this email.

        Thank you for choosing Credit Smart
        — Smart Credit. Smarter Decisions.

        Best regards,
        Credit Smart Team
        """
        email_msg = EmailMessage()
        email_msg['From'] = config_data['notification']['email']['email_sender']
        email_msg['To'] = email_id 
        email_msg['Subject'] = "OTP verification For credit Smart Application"
        email_msg.set_content(contents)  #set email message template 

        #login with email address details
        smtp_server = config_data['notification']['server']['email-server']
        smtp_port = int(config_data['notification']['server']['email-port'])

        with SMTP(smtp_server, smtp_port) as email_server:
            email_server.starttls()  #start TLS server
            #login with Google credentials 
            email_server.login(
                config_data['notification']['email']['email_sender'],
                config_data['notification']['email']['email_password'])
            email_server.send_message(email_msg)
        return {"Message : OTP sent  successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#create checkpoints for verify User otp 
@routers.post('/auth/Verify_OTP')
async def verify_otp(request_2 : OTP_Verification_Wrapper):

    """ Request user OTP from client session"""
    user_input_otp = request_2.user_otp

    """ Request Email address from Client Session"""
    email_id = request_2.email_address

    #connect with redis session
    redis_conn = connect_redis_server(
            redis_host=config_data['redis']['host'],
            redis_port=config_data['redis']['port'] 
    )
    #fetch store session from redis 
    store_session = get_otp_from_redis(email_address=email_id,redis_connection=redis_conn)

    #call verification method to Verify otp
    verification_status = verify_user_otp_number(
        email_address=email_id,user_otp=user_input_otp,
        redis_connection=redis_conn,generated_otp=generated_otp)

    if verification_status is True:
        return {"Message Status : OTP verified Successfully"}
    elif verification_status is False:
        return {"Message Status : Invalid OTP"}
    else:
        return {"Message Status : No otp found in session"}
    
#add routers for log in and registers for user 
@routers.post('/auth/register')
async def register_user(request_3 : UserRegisteration):

    """
Registers a new user in the Credit Smart application.

This API endpoint accepts user registration details such as full name, email,
phone number, username, and password. It validates that no field is empty and
then inserts the user record into the MySQL database.

Raises:
    HTTPException: 
        - 400 Bad Request if any required field is missing/empty.
        - 500 Internal Server Error if database insertion fails.

Returns:
    dict: Success message after user registration is completed.
"""

    #check user request to store the User Registeration data into Database
    if not request_3:

        raise HTTPException(status_code=400,detail="Bad Request")


        #check whether if any field is empty of not 
    if (request_3.full_name.strip() == "" or 
        request_3.email.strip() == "" or 
        request_3.Username.strip() == "" or 
        request_3.phone.strip() == "" or 
        request_3.password.strip() == ""):
        
        raise HTTPException(status_code=400,detail="All fields are required")
        
    #store the registeration detail to mysql database
    # store the registration detail to mysql database
    registeration_query = f"""
        INSERT INTO {MYSQL_TABLE} (full_name, email, phone, password, Username)
        VALUES (%s, %s, %s, %s, %s)
    """

    connection_cursor_obj.execute(registeration_query, (
        request_3.full_name,
        request_3.email,
        request_3.phone,
        request_3.password,
        request_3.Username
    ))
    
    #create an commit in mysql connection to store data 
    connection.commit()

        
    #close the cursor object and connection for each request
    connection_cursor_obj.close()

    connection.close()

    return {
        "message": "User registered successfully"
    }

#add routers to login authentication for user 
@routers.post('/auth/login')
async def user_login(request_4 : UserLogin):

    """
    """
    if request_4.Username.strip() == "" or request_4.password.strip == "":

        raise HTTPException(
            status_code=400,
            detail="username and Password cannot be empty"
        )
    
    #verify user login authentication by call procedure
    procedure_name = "user_login"
    login_query = f""" CALL {procedure_name}(%s)"""

    connection_cursor_obj.execute(login_query,(request_4.Username))

    #fetch the password from db
    result = connection_cursor_obj.fetchone()  #return type tuple
 
    if result is None:

        return {"Message":"No Username and password found ! Invalid Credentials"}
    
    fetched_username = result[0].strip()
    fetched_password = result[1].strip()

    print(f" Fetch password {fetched_password} and {fetched_username}")
    #check the user login request and password but using comparision operator 
    if request_4.password.strip() == fetched_password:
        return {"Message":"Login Success"}
    else:
        return {"Message":"Invalid Password"}
    
#add Update functionality to update password based on user email
@routers.put('/auth/update_password')
async def update_user_password(payload : UpdatePassword):

    """
    Docstring for update_user_password
    
    :param payload: Description
    :type payload: UpdatePassword
    """

    #connect with SQL to fetch registered user id
    connection_cursor_obj.execute(f"SELECT user_id from {MYSQL_TABLE} WHERE email = %s",(payload.email.strip()))

    #fetch the tuple data 
    user = connection_cursor_obj.fetchone()

    print(user)

    if not user:

        raise HTTPException(status_code=402,detail="User Not found")
    
    #fetch user id from result tuple
    user_id = user[0]

    #call procedure to update password 
    connection_cursor_obj.execute("CALL Update_Password(%s,%s)",(
        payload.new_password.strip(),
        user_id
        ))

    #make commit connection 
    connection.commit()

    return {"Message":"Password Updated Successfully"}

# Include routers checkpoints in FAST API backend service
app.include_router(routers)

if __name__ == '__main__':

    #run FAST API Application run with running configuration
    uvicorn.run(app, host=config_data['server']['host'], port=config_data['server']['port'])
