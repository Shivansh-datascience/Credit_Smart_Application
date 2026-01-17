from auth.OTP_generator import generate_OTP_authentication, connect_redis_server
from auth.OTP_session import store_otp_in_redis, get_otp_from_redis , verify_user_otp_number
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="D:\\credit_scoring_project\\.env")
Redis_host = os.getenv("Redis_host")
Redis_port = int(os.getenv("Redis_running_port"))

# Connect Redis
redis_conn = connect_redis_server(redis_host=Redis_host, redis_port=Redis_port)

# Step 1: Generate OTP
key, otp = generate_OTP_authentication("shivanshbajpai2011@gmail.com")
print(f"Generated_OTP (for testing): {otp.now()}")  # just print the integer OTP

# Step 2: Store OTP in Redis
store_otp_in_redis(email_address="shivanshbajpai2011@gmail.com",secret_key=key,generated_otp=otp.now(),redis_connection=redis_conn)
#step 3- Fect OTP from redis
fetch_session = get_otp_from_redis(email_address="shivanshbajpai2011@gmail.com",redis_connection=redis_conn)
print(f" {fetch_session}")

#step 4- verify
user_input = str(input("Enter OTP :"))
verification = verify_user_otp_number("shivanshbajpai2011@gmail.com",user_otp=user_input,
                                      redis_connection=redis_conn,
                                      generated_otp=otp)
if verification is True:
    print("OTP verfication Test : Passed")  #display result if Verification status test passed
    print("OTP verified")
elif verification is False:
    print("OTP verification Test : Failed")
    print("OTP not verified") 
else:
    print(verification)  #display result if session not found in redis session state 
