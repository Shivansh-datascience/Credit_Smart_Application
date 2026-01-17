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
