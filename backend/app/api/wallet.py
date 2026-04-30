from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from math import ceil
from datetime import datetime
import uuid

from ..database import get_db
from ..models.models import User, Wallet, Transaction, RechargeRecord
from ..schemas.wallet import (
    WalletResponse, TransactionResponse, TransactionListResponse,
    RechargeCreate, RechargeResponse, TransferCreate
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user

router = APIRouter(prefix="/wallet", tags=["钱包"])


@router.get("", response_model=WalletResponse, summary="获取钱包信息")
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户钱包信息"""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        # Create wallet if not exists
        wallet = Wallet(user_id=current_user.id, balance=0.0, frozen_amount=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return wallet


@router.get("/transactions", response_model=TransactionListResponse, summary="获取交易记录")
async def get_transactions(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取交易记录"""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    
    if not wallet:
        return TransactionListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0
        )
    
    query = db.query(Transaction).filter(Transaction.wallet_id == wallet.id)
    
    if type:
        query = query.filter(Transaction.type == type)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    transactions = query.order_by(desc(Transaction.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return TransactionListResponse(
        items=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/recharge", response_model=RechargeResponse, summary="充值")
async def create_recharge(
    recharge_data: RechargeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建充值订单"""
    order_no = f"RC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    
    recharge = RechargeRecord(
        user_id=current_user.id,
        amount=recharge_data.amount,
        payment_method=recharge_data.payment_method,
        order_no=order_no,
        status="pending"
    )
    
    db.add(recharge)
    db.commit()
    db.refresh(recharge)
    
    return recharge


@router.post("/recharge/{order_no}/confirm", response_model=SuccessResponse, summary="确认充值")
async def confirm_recharge(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """确认充值（模拟支付回调）"""
    recharge = db.query(RechargeRecord).filter(
        RechargeRecord.order_no == order_no,
        RechargeRecord.user_id == current_user.id
    ).first()
    
    if not recharge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="充值记录不存在"
        )
    
    if recharge.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="充值状态不正确"
        )
    
    # Update wallet balance
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0.0, frozen_amount=0.0)
        db.add(wallet)
        db.flush()
    
    wallet.balance += recharge.amount
    
    # Create transaction record
    transaction = Transaction(
        wallet_id=wallet.id,
        user_id=current_user.id,
        amount=recharge.amount,
        balance_after=wallet.balance,
        type="recharge",
        status="completed",
        description=f"充值 - {recharge.payment_method}"
    )
    db.add(transaction)
    
    # Update recharge status
    recharge.status = "success"
    recharge.paid_at = datetime.utcnow()
    
    db.commit()
    
    return SuccessResponse(message="充值成功")


@router.post("/transfer", response_model=SuccessResponse, summary="转账")
async def transfer(
    transfer_data: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """向其他用户转账"""
    if transfer_data.to_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己转账"
        )
    
    # Check recipient exists
    recipient = db.query(User).filter(User.id == transfer_data.to_user_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收款用户不存在"
        )
    
    # Check sender balance
    from decimal import Decimal
    amount_decimal = Decimal(str(transfer_data.amount))
    
    sender_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not sender_wallet or sender_wallet.balance < amount_decimal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="余额不足"
        )
    
    # Get or create recipient wallet
    recipient_wallet = db.query(Wallet).filter(Wallet.user_id == transfer_data.to_user_id).first()
    if not recipient_wallet:
        recipient_wallet = Wallet(user_id=transfer_data.to_user_id, balance=0.0, frozen_amount=0.0)
        db.add(recipient_wallet)
        db.flush()
    
    # Transfer
    from decimal import Decimal
    
    amount_decimal = Decimal(str(transfer_data.amount))
    sender_wallet.balance -= amount_decimal
    recipient_wallet.balance += amount_decimal
    
    # Create transaction records
    description = transfer_data.description or f"转账给{recipient.name}"
    
    sender_transaction = Transaction(
        wallet_id=sender_wallet.id,
        user_id=current_user.id,
        amount=-amount_decimal,
        balance_after=sender_wallet.balance,
        type="transfer_out",
        status="completed",
        description=description,
        related_user_id=recipient.id
    )
    
    recipient_transaction = Transaction(
        wallet_id=recipient_wallet.id,
        user_id=recipient.id,
        amount=amount_decimal,
        balance_after=recipient_wallet.balance,
        type="transfer_in",
        status="completed",
        description=f"来自{current_user.name}的转账",
        related_user_id=current_user.id
    )
    
    db.add_all([sender_transaction, recipient_transaction])
    db.commit()
    
    return SuccessResponse(message="转账成功")
