#create an Input validation for model input 
from pydantic import BaseModel , Field

#class for validation
class UserCreditDataRequest(BaseModel):
    credit_mix: float = Field(...,description="Normalized credit mix")
    annual_income: float = Field(...,description="Annual income")
    num_bank_accounts: float = Field(..., description="Number of bank accounts")
    num_credit_card: float = Field(...,description="Number of credit cards")
    interest_rate: float = Field(..., ge=0, le=100, description="Interest rate (%)")
    num_of_loan: float = Field(..., ge=0, description="Number of active loans")
    delay_from_due_date: float = Field(...,description="Days delayed")
    changed_credit_limit: float = Field(..., description="Change in credit limit")
    outstanding_debt: float = Field(...,description="Outstanding debt amount")
    total_emi_per_month: float = Field(...,description="Total EMI per month")
    risk_spending: float = Field(...,description="Risk spending index")
    financial_stress_index: float = Field(..., description="Financial stress score")
    debt_to_income_ratio: float = Field(...,description="Debt to income ratio")
    payment_of_min_amount: float = Field(...,description="Min payment encoded")
