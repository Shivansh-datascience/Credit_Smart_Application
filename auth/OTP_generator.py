import pyotp
import redis
import os
from redis import ConnectionError
from pyotp.totp import TOTP  #time base otp authentication
from pyotp.utils import build_uri  #for generating an otp in link format
from pyotp.contrib import steam  #for generating otp session

def generate_OTP_authentication(email_address: str):

    """ Apply OTP authentication for Application Dashboard"""
    try:
        
        #generate base number for otp auth with characters sequence with 32 bit length
        sequence_of_secret_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        random_base_number = pyotp.random_base32(
            length=32,chars=sequence_of_secret_key)
        
        #create an otp variable object for generating otp time based 
        generated_otp = pyotp.TOTP(s=random_base_number,
                                   digits=6,
                                   interval=300)  #300 seconds time limit for otp authentication

        #call object with return type as otp for 6 digits
        return random_base_number , generated_otp  #return otp number along with secret key
    except BaseException as e:
        return f" Error in Generation OTP {e}"  #return base exception error
    
#add additional print() line to debug otp generation function in terminal
#secret_key , generated_otp = generate_OTP_authentication(
    #mobile_number="7449253009")
#print(f" OTP generated {generated_otp} with secret_key : {secret_key} within time Interval 60 seconds")
def connect_redis_server(redis_host,redis_port):
    
    """ Connect with redis server for OTP management"""
    try:
        redis_connection = redis.Redis(
            host=redis_host,
            port = redis_port,
            db = 0, #dont make connection to database
            encoding="utf-8",
            decode_responses=True  #make response visible
        )
        return redis_connection #return redis connection object
    except redis.ConnectionError as connection_error:
        return f" Redis server status : {connection_error}"


