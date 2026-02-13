from pydantic import BaseModel, EmailStr, Field
from typing import Optional


#wrapper for Generating OTP (2FA)
class OTP_Validation_Wrapper(BaseModel):
    email_address: EmailStr = Field(..., description="email address for OTP Verification")
    mobile_number: Optional[str] = None

#wrapper for verify OTP (2FA)
class OTP_Verification_Wrapper(BaseModel):
    email_address : EmailStr = Field(..., description="Email address for OTP session verification")
    user_otp : str = Field(..., description="User OTP for verification")

#wrapper for Registeration
class UserRegisteration(BaseModel):
    full_name : str = Field(..., description="Full Name for User")
    email : EmailStr = Field(..., description="Email for User Registeration")
    Username : str = Field(..., description="Username for Registeration")
    phone : str = Field(..., description="Phone number for Registeration")
    password : str = Field(..., description="password for User Registeration")

#wrapper for User Login
class UserLogin(BaseModel):
    Username : str = Field(..., description="Username for User login")
    password : str = Field(..., description="Password for user login")

#wrapper for update account username and password
class UpdateUsername(BaseModel):
    email : str = Field(..., description="Email for User")
    new_username : str = Field(..., description="user new Username")

class UpdatePassword(BaseModel):
    email : str = Field(..., description="email for User")
    new_password : str = Field(..., description="user new password")
