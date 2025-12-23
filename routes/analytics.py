from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from collections import defaultdict
from models import (
    CategoryStatistics, PeriodStatistics, ExpenseDynamics, 
    AnalyticsResponse
)
from routes.auth import get_current_user
from utils import get_user_transactions, get_category_by_id

router = APIRouter(prefix="/analytics", tags=["Аналитика финансов"])

@router.get("/statistics", response_model=AnalyticsResponse)
async def get_financial_statistics(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)")
):
    transactions = get_user_transactions(current_user["id"])
    
    if start_date:
        transactions = [t for t in transactions if t["transaction_date"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["transaction_date"] <= end_date]
    
    total_income = 0.0
    total_expense = 0.0
    income_by_category = defaultdict(lambda: {"amount": 0.0, "count": 0})
    expense_by_category = defaultdict(lambda: {"amount": 0.0, "count": 0})
    
    for transaction in transactions:
        amount = transaction["amount"]
        category_id = transaction["category_id"]
        
        if transaction["type"] == "income":
            total_income += amount
            income_by_category[category_id]["amount"] += amount
            income_by_category[category_id]["count"] += 1
        elif transaction["type"] == "expense":
            total_expense += amount
            expense_by_category[category_id]["amount"] += amount
            expense_by_category[category_id]["count"] += 1
    
    income_categories = []
    for category_id, data in income_by_category.items():
        category = get_category_by_id(category_id)
        if category:
            percentage = (data["amount"] / total_income * 100) if total_income > 0 else 0
            income_categories.append(
                CategoryStatistics(
                    category_name=category["name"],
                    category_id=category_id,
                    total_amount=data["amount"],
                    transaction_count=data["count"],
                    percentage=round(percentage, 2)
                )
            )
    
    expense_categories = []
    for category_id, data in expense_by_category.items():
        category = get_category_by_id(category_id)
        if category:
            percentage = (data["amount"] / total_expense * 100) if total_expense > 0 else 0
            expense_categories.append(
                CategoryStatistics(
                    category_name=category["name"],
                    category_id=category_id,
                    total_amount=data["amount"],
                    transaction_count=data["count"],
                    percentage=round(percentage, 2)
                )
            )
    
    income_categories.sort(key=lambda x: x.total_amount, reverse=True)
    expense_categories.sort(key=lambda x: x.total_amount, reverse=True)
    
    expense_dynamics = []
    expense_by_date = defaultdict(float)
    
    for transaction in transactions:
        if transaction["type"] == "expense":
            date = transaction["transaction_date"]
            expense_by_date[date] += transaction["amount"]

    for date in sorted(expense_by_date.keys()):
        expense_dynamics.append(
            ExpenseDynamics(
                date=date,
                amount=expense_by_date[date]
            )
        )
    
    balance = total_income - total_expense
    
    return AnalyticsResponse(
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        expense_by_category=expense_categories,
        income_by_category=income_categories,
        expense_dynamics=expense_dynamics
    )


@router.get("/expenses/dynamics", response_model=List[ExpenseDynamics])
async def get_expense_dynamics(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)")
):
    transactions = get_user_transactions(current_user["id"])
    
    transactions = [t for t in transactions if t["type"] == "expense"]
    
    if start_date:
        transactions = [t for t in transactions if t["transaction_date"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["transaction_date"] <= end_date]
    
    expense_by_date = defaultdict(float)
    
    for transaction in transactions:
        date = transaction["transaction_date"]
        expense_by_date[date] += transaction["amount"]
    
    dynamics = []
    for date in sorted(expense_by_date.keys()):
        dynamics.append(
            ExpenseDynamics(
                date=date,
                amount=expense_by_date[date]
            )
        )
    
    return dynamics


@router.get("/categories/{category_id}/statistics", response_model=CategoryStatistics)
async def get_category_statistics(
    category_id: int,
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)")
):
    category = get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Категория не найдена"
        )
    
    if category["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Нет доступа к этой категории"
        )
    
    transactions = get_user_transactions(current_user["id"])
    
    transactions = [t for t in transactions if t["category_id"] == category_id]
    
    if start_date:
        transactions = [t for t in transactions if t["transaction_date"] >= start_date]
    if end_date:
        transactions = [t for t in transactions if t["transaction_date"] <= end_date]
    
    total_amount = sum(t["amount"] for t in transactions)
    transaction_count = len(transactions)
   
    all_same_type = [t for t in get_user_transactions(current_user["id"]) 
                     if t["type"] == category["type"]]
    total_same_type = sum(t["amount"] for t in all_same_type)
    percentage = (total_amount / total_same_type * 100) if total_same_type > 0 else 0
    
    return CategoryStatistics(
        category_name=category["name"],
        category_id=category_id,
        total_amount=total_amount,
        transaction_count=transaction_count,
        percentage=round(percentage, 2)
    )


@router.get("/summary", response_model=dict)
async def get_summary(current_user: dict = Depends(get_current_user)):
   
    transactions = get_user_transactions(current_user["id"])
    
    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expense
    
    income_count = sum(1 for t in transactions if t["type"] == "income")
    expense_count = sum(1 for t in transactions if t["type"] == "expense")
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "income_count": income_count,
        "expense_count": expense_count,
        "total_transactions": len(transactions)
    }

