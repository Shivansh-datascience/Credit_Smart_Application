import yaml
from smtplib import SMTP 
import requests
from email.message import  EmailMessage
from fastapi import FastAPI, HTTPException, Request, APIRouter
from auth.OTP_generator import connect_redis_server, generate_OTP_authentication
from auth.OTP_session import store_otp_in_redis, get_otp_from_redis, verify_user_otp_number
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from .validation import OTP_Validation_Wrapper , OTP_Verification_Wrapper  # Fixed import
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()

#load API key from environment variable s
fast2_sms_api_key = os.getenv("fast2_sms_api_key")

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
    
# Include routers checkpoints in FAST API backend service
app.include_router(routers)

if __name__ == '__main__':

    #run FAST API Application run with running configuration
    uvicorn.run(app, host=config_data['server']['host'], port=config_data['server']['port'])
