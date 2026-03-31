from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status, Query
from typing import List, Optional
from models import (
    BudgetCreate,
    Budget,
    BudgetUpdate,
    BudgetStatus,
    BudgetTopUp,
    BudgetSpend,
    MessageResponse,
)
from routes.auth import get_current_user
from utils import (
    create_budget,
    create_transaction,
    get_user_budgets,
    get_user_budgets_for_display,
    get_user_budget_periods,
    delete_budget,
    update_budget,
    get_category_by_id,
    get_user_transactions,
)

router = APIRouter(prefix="/budgets", tags=["Управление бюджетом"])


def _default_spend_date_for_period(period: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    if today.startswith(period):
        return today
    return f"{period}-15"


def _resolve_user_budget(user_id: int, budget_id: int) -> Optional[dict]:
    budgets = get_user_budgets(user_id)
    return next((b for b in budgets if b["id"] == budget_id), None)


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
            detail="Неверный формат периода."
        )
    
    budget = create_budget(
        user_id=current_user["id"],
        category_id=budget_data.category_id,
        limit_amount=budget_data.limit_amount,
        period=budget_data.period
    )
    
    return calculate_budget_status(budget, current_user["id"])

@router.get("/status", response_model=List[BudgetStatus])
async def get_budget_status(
    request: Request,
    all_periods: bool = Query(
        False,
        description="Если true — все месяцы; иначе только текущий календарный месяц (YYYY-MM)",
    ),
    period: Optional[str] = Query(
        None,
        description="Показать бюджеты только за указанный период YYYY-MM (приоритетнее all_periods)",
    ),
):
    current_user = await get_current_user(request)
    budgets = get_user_budgets_for_display(
        current_user["id"],
        period=period,
        all_periods=all_periods,
    )

    budget_statuses = []
    for budget in budgets:
        budget_statuses.append(calculate_budget_status(budget, current_user["id"]))

    budget_statuses.sort(key=lambda x: x.percentage_used, reverse=True)

    return budget_statuses


@router.get("/periods", response_model=List[str])
async def list_budget_periods(request: Request):
    current_user = await get_current_user(request)
    return get_user_budget_periods(current_user["id"])


@router.post("/{budget_id}/top-up", response_model=BudgetStatus)
async def budget_top_up(
    budget_id: int,
    body: BudgetTopUp,
    request: Request,
):
    current_user = await get_current_user(request)
    budget = _resolve_user_budget(current_user["id"], budget_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бюджет не найден",
        )
    new_limit = budget["limit_amount"] + body.amount
    if new_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Итоговый лимит должен быть больше нуля",
        )
    updated = update_budget(budget_id, limit_amount=new_limit)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить лимит",
        )
    return calculate_budget_status(updated, current_user["id"])


@router.post("/{budget_id}/spend", response_model=BudgetStatus)
async def budget_spend(
    budget_id: int,
    body: BudgetSpend,
    request: Request,
):
    current_user = await get_current_user(request)
    budget = _resolve_user_budget(current_user["id"], budget_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бюджет не найден",
        )
    category = get_category_by_id(budget["category_id"])
    if not category or category.get("type") != "expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бюджет привязан к недопустимой категории",
        )
    if body.transaction_date is None:
        tx_date = _default_spend_date_for_period(budget["period"])
    else:
        tx_date = str(body.transaction_date)
        if not tx_date.startswith(budget["period"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Дата должна относиться к периоду бюджета {budget['period']}",
            )
    create_transaction(
        user_id=current_user["id"],
        category_id=budget["category_id"],
        amount=body.amount,
        transaction_type="expense",
        transaction_date=tx_date,
        description=body.description,
    )
    return calculate_budget_status(budget, current_user["id"])


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


@router.put("/{budget_id}", response_model=BudgetStatus)
async def update_budget_by_id(
    budget_id: int,
    budget_update: BudgetUpdate,
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
    
    update_data = {}
    
    if budget_update.category_id is not None:
        category = get_category_by_id(budget_update.category_id)
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
        update_data["category_id"] = budget_update.category_id
    
    if budget_update.limit_amount is not None:
        update_data["limit_amount"] = budget_update.limit_amount
    
    if budget_update.period is not None:
        try:
            year, month = budget_update.period.split("-")
            if len(year) != 4 or len(month) != 2:
                raise ValueError
            int(year)
            int(month)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат периода. Используйте формат YYYY-MM (например: 2024-01)"
            )
        update_data["period"] = budget_update.period
    
    updated_budget = update_budget(budget_id, **update_data)
    
    if not updated_budget:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении бюджета"
        )
    
    return calculate_budget_status(updated_budget, current_user["id"])


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
