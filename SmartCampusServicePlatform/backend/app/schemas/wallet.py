from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    recharge = "recharge"
    withdraw = "withdraw"
    task_reward = "task_reward"
    task_payment = "task_payment"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"


class TransactionStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class RechargeStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


# Wallet schemas
class WalletResponse(BaseModel):
    id: int
    user_id: int
    balance: float
    frozen_amount: float
    total_income: float = 0
    total_expense: float = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Transaction schemas
class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    type: TransactionType
    description: Optional[str] = Field(None, max_length=500)
    related_id: Optional[int] = None


class TransactionResponse(BaseModel):
    id: int
    wallet_id: int
    amount: float
    type: TransactionType
    status: TransactionStatus
    description: Optional[str] = None
    related_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Recharge schemas
class RechargeCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., max_length=50)


class RechargeResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    payment_method: str
    status: RechargeStatus
    order_no: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Transfer schemas
class TransferCreate(BaseModel):
    to_user_id: int
    amount: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
