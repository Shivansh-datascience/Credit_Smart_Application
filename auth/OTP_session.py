import pyotp
from pydantic import BaseModel, Field
import os
import json
from dotenv import load_dotenv
from datetime import time
from pyotp.totp import TOTP  # time base otp authentication
from pyotp.utils import build_uri  # for generating an otp in link format
from pyotp.contrib import steam  # for generating otp session
from auth.OTP_generator import generate_OTP_authentication, connect_redis_server

load_dotenv(dotenv_path="D:\credit_scoring_project\.env", encoding="utf-8")
Redis_host = str(os.getenv("Redis_host"))
Redis_port = int(os.getenv("Redis_running_port"))

# call connection method in current file 
redis_connection = connect_redis_server(
    redis_host=Redis_host,
    redis_port=Redis_port
)

# check redis server status by ping redis server address
print(f" Redis server status : {redis_connection.ping()}")


# create an method to store otp in redis cache
def store_otp_in_redis(email_address, secret_key, generated_otp, redis_connection):
    """
    Stores the generated OTP securely in Redis for the given mobile number.

    This method saves the OTP along with a secret key in Redis, enabling
    temporary and secure OTP verification. The stored OTP is typically
    associated with an expiration time (TTL) to ensure it remains valid
    only for a limited duration and cannot be reused.

    Parameters:
        email address(str): The user's email id used as the unique
                             identifier for storing the OTP.
        secret_key (str): A secret key used for encrypting or hashing
                          the OTP before storage.
        generated_otp (int): The one-time password generated for the user.
        redis_connection: An active Redis connection instance used
                          to store the OTP data.

    Returns:
        session data : Returns stored session data object 
    """
    try:
        # create an dict format data for storing otp data into redis
        session_data = {
            "OTP": generated_otp,  #store OTP in redis session
            "email_address": email_address,  #store email Address in redis session
            "Secret_key": secret_key,  #store unique secret key with OTP details
        }

        # set session data into redis using json parsing with TTL 300 sec
        redis_connection.set(name=f"otp:{email_address}", value=json.dumps(session_data), ex=300)
        return session_data  # return stored session data 
    except Exception as e:
        return e   # return exception message

# method for fetching otp session from redis server
def get_otp_from_redis(email_address, redis_connection):
    """
    Retrieves the OTP authentication session from Redis for the given mobile number.

    This method fetches the stored OTP session associated with the user's
    mobile number and refreshes its expiration time to maintain session
    validity during the verification process. The session data is returned
    as a JSON object if available.

    Parameters:
        mobile_number (str): The user's mobile number used to identify
                             the OTP session in Redis.

    Returns:
        dict | None:
            - dict: OTP session data in JSON format if the session exists.
            - None: If no OTP session is found or the session has expired.
    """
    time_limit = 300
    key = f"otp:{email_address}"  # remove leading space
    redis_otp_session = redis_connection.get(key)
    if redis_otp_session:
        redis_connection.expire(key, time_limit)  # refresh TTL
        return json.loads(redis_otp_session)
    else:
        return None

# create otp verification by user input with redis session stored
def verify_user_otp_number(email_address: str, user_otp: str, redis_connection,generated_otp):
    """
    Verifies the OTP entered by the user for the given mobile number using stored session data.

    Returns:
        str | bool: Error message if no session, True if verified, False otherwise
    """
    # Fetch stored OTP session
    key = f"otp:{email_address}"
    #fetch key from redis session 
    redis_data = redis_connection.get(key)

    # ✅ Session check
    if redis_data is None:
        return "OTP not found in session"  #return message if otp not found in redis session
    else:
        verification_result = generated_otp.verify(str(user_otp),valid_window=0)  #shift time range after completion of define time
        if verification_result:
            redis_connection.delete(f"otp:{email_address}")
            return True
        else:
            return False
