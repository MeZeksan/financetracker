from fastapi import APIRouter, HTTPException, Request, status
from typing import List
from models import BudgetCreate, Budget, BudgetStatus, MessageResponse
from routes.auth import get_current_user
from utils import (
    create_budget, get_user_budgets, delete_budget,
    get_category_by_id, get_user_transactions
)

router = APIRouter(prefix="/budgets", tags=["Управление бюджетом"])

def calculate_budget_status(budget: dict, user_id: int) -> BudgetStatus:
    category = get_category_by_id(budget["category_id"])
    
    transactions = get_user_transactions(user_id)
    
    period = budget["period"]
    spent_amount = 0.0
    
    for transaction in transactions:
        if (transaction["category_id"] == budget["category_id"] and 
            transaction["type"] == "expense" and
            transaction["transaction_date"].startswith(period)):
            spent_amount += transaction["amount"]
    
    remaining_amount = budget["limit_amount"] - spent_amount
    percentage_used = (spent_amount / budget["limit_amount"] * 100) if budget["limit_amount"] > 0 else 0
    
    return BudgetStatus(
        id=budget["id"],
        user_id=budget["user_id"],
        category_id=budget["category_id"],
        limit_amount=budget["limit_amount"],
        period=budget["period"],
        created_at=budget["created_at"],
        category_name=category["name"] if category else "Неизвестная категория",
        spent_amount=spent_amount,
        remaining_amount=remaining_amount,
        percentage_used=round(percentage_used, 2)
    )

@router.post("/", response_model=BudgetStatus, status_code=status.HTTP_201_CREATED)
async def create_new_budget(
    budget_data: BudgetCreate,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(budget_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    if category["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой категории"
        )
    
    if category["type"] != "expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бюджет можно создавать только для категорий расходов"
        )
    
    try:
        year, month = budget_data.period.split("-")
        if len(year) != 4 or len(month) != 2:
            raise ValueError
        int(year)
        int(month)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат периода. Используйте формат YYYY-MM (например: 2024-01)"
        )
    
    budget = create_budget(
        user_id=current_user["id"],
        category_id=budget_data.category_id,
        limit_amount=budget_data.limit_amount,
        period=budget_data.period
    )
    
    return calculate_budget_status(budget, current_user["id"])


@router.get("/status", response_model=List[BudgetStatus])
async def get_budget_status(request: Request):
    current_user = await get_current_user(request)
    budgets = get_user_budgets(current_user["id"])
    
    budget_statuses = []
    for budget in budgets:
        status = calculate_budget_status(budget, current_user["id"])
        budget_statuses.append(status)
    
    budget_statuses.sort(key=lambda x: x.percentage_used, reverse=True)
    
    return budget_statuses


@router.get("/{budget_id}", response_model=BudgetStatus)
async def get_budget_by_id(
    budget_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    budgets = get_user_budgets(current_user["id"])
    budget = next((b for b in budgets if b["id"] == budget_id), None)
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бюджет не найден"
        )
    
    return calculate_budget_status(budget, current_user["id"])


@router.delete("/{budget_id}", response_model=MessageResponse)
async def delete_budget_by_id(
    budget_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    budgets = get_user_budgets(current_user["id"])
    budget = next((b for b in budgets if b["id"] == budget_id), None)
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бюджет не найден"
        )
    
    success = delete_budget(budget_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении бюджета"
        )
    
    return MessageResponse(
        message="Бюджет успешно удален",
        detail=f"Бюджет #{budget_id} был удален"
    )
