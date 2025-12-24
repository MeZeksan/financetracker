from fastapi import APIRouter, HTTPException, Request, status, Query
from typing import List, Optional
from models import (
    TransactionCreate, Transaction, TransactionResponse,
    CategoryCreate, Category, CategoryUpdate, MessageResponse
)
from routes.auth import get_current_user
from utils import (
    create_transaction, get_user_transactions, get_transaction_by_id,
    delete_transaction, create_category, get_user_categories,
    get_category_by_id, update_category, delete_category
)

router = APIRouter(prefix="/transactions", tags=["Управление транзакциями"])

@router.post("/categories", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_new_category(
    category_data: CategoryCreate,
    request: Request
):
    current_user = await get_current_user(request)
    category = create_category(
        user_id=current_user["id"],
        name=category_data.name,
        category_type=category_data.type
    )
    
    return Category(**category)

@router.get("/categories", response_model=List[Category])
async def get_categories(request: Request):
    current_user = await get_current_user(request)
    categories = get_user_categories(current_user["id"])
    return [Category(**cat) for cat in categories]


@router.get("/categories/{category_id}", response_model=Category)
async def get_category_by_id_endpoint(
    category_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(category_id)
    
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
    
    return Category(**category)


@router.put("/categories/{category_id}", response_model=Category)
async def update_category_by_id(
    category_id: int,
    category_update: CategoryUpdate,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(category_id)
    
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
    
    update_data = {}
    if category_update.name is not None:
        update_data["name"] = category_update.name
    if category_update.type is not None:
        update_data["type"] = category_update.type.value
    
    updated_category = update_category(category_id, **update_data)
    
    if not updated_category:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении категории"
        )
    
    return Category(**updated_category)


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category_by_id(
    category_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(category_id)
    
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
    
    success = delete_category(category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении категории"
        )
    
    return MessageResponse(
        message="Категория успешно удалена",
        detail=f"Категория '{category['name']}' была удалена"
    )


@router.post("/income", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_income(
    transaction_data: TransactionCreate,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(transaction_data.category_id)
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
    
    if transaction_data.type != "income":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для добавления дохода тип транзакции должен быть 'income'"
        )
    
    transaction = create_transaction(
        user_id=current_user["id"],
        category_id=transaction_data.category_id,
        amount=transaction_data.amount,
        transaction_type=transaction_data.type,
        transaction_date=str(transaction_data.transaction_date),
        description=transaction_data.description
    )
    
    response = TransactionResponse(**transaction)
    response.category_name = category["name"]
    
    return response


@router.post("/expense", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_expense(
    transaction_data: TransactionCreate,
    request: Request
):
    current_user = await get_current_user(request)
    category = get_category_by_id(transaction_data.category_id)
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
    
    if transaction_data.type != "expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для добавления расхода тип транзакции должен быть 'expense'"
        )
    
    transaction = create_transaction(
        user_id=current_user["id"],
        category_id=transaction_data.category_id,
        amount=transaction_data.amount,
        transaction_type=transaction_data.type,
        transaction_date=str(transaction_data.transaction_date),
        description=transaction_data.description
    )
    
    response = TransactionResponse(**transaction)
    response.category_name = category["name"]
    
    return response


@router.get("/history", response_model=List[TransactionResponse])
async def get_transaction_history(
    request: Request,
    transaction_type: Optional[str] = Query(None, description="Фильтр по типу (income/expense)")
):
    current_user = await get_current_user(request)
    transactions = get_user_transactions(current_user["id"])
    
    if transaction_type:
        transactions = [t for t in transactions if t["type"] == transaction_type]
    
    transactions.sort(key=lambda x: x["transaction_date"], reverse=True)
    
    result = []
    for transaction in transactions:
        category = get_category_by_id(transaction["category_id"])
        response = TransactionResponse(**transaction)
        response.category_name = category["name"] if category else None
        result.append(response)
    
    return result


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    transaction = get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транзакция не найдена"
        )
    
    if transaction["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой транзакции"
        )
    
    category = get_category_by_id(transaction["category_id"])
    response = TransactionResponse(**transaction)
    response.category_name = category["name"] if category else None
    
    return response


@router.delete("/{transaction_id}", response_model=MessageResponse)
async def delete_transaction_by_id(
    transaction_id: int,
    request: Request
):
    current_user = await get_current_user(request)
    transaction = get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транзакция не найдена"
        )
    
    if transaction["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой транзакции"
        )
    
    success = delete_transaction(transaction_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении транзакции"
        )
    
    return MessageResponse(
        message="Транзакция успешно удалена",
        detail=f"Транзакция #{transaction_id} была удалена"
    )
