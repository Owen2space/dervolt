from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime
from models import UserRole, TransactionType, TransactionStatus

class UserBase(BaseModel):
    email: EmailStr
    first_name: constr(min_length=2, max_length=50)
    last_name: constr(min_length=2, max_length=50)
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: constr(min_length=8)

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

class AccountBase(BaseModel):
    account_type: str
    currency: str = "USD"

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    account_number: str
    balance: float
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class TransactionBase(BaseModel):
    account_id: int
    transaction_type: TransactionType
    amount: float
    payment_method: str
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    status: TransactionStatus
    reference: str
    created_at: datetime

    class Config:
        orm_mode = True 