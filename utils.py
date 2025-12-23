from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt

SECRET_KEY = "secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

storage = {
    "users": [],
    "categories": [],
    "transactions": [],
    "budgets": [],
    "goals": []
}

counters = {
    "users": 1,
    "categories": 1,
    "transactions": 1,
    "budgets": 1,
    "goals": 1
}

def get_next_id(entity_type: str) -> int:
    current_id = counters[entity_type]
    counters[entity_type] += 1
    return current_id

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    for user in storage["users"]:
        if user["email"] == email:
            return user
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    for user in storage["users"]:
        if user["id"] == user_id:
            return user
    return None


def create_user(full_name: str, email: str, password: str) -> Dict[str, Any]:
    user = {
        "id": get_next_id("users"),
        "full_name": full_name,
        "email": email,
        "password": get_password_hash(password),
        "created_at": datetime.utcnow()
    }
    storage["users"].append(user)
    return user


def update_user(user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    if "password" in kwargs and kwargs["password"]:
        kwargs["password"] = get_password_hash(kwargs["password"])
    
    for key, value in kwargs.items():
        if value is not None:
            user[key] = value
    
    return user


def delete_user(user_id: int) -> bool:
    for i, user in enumerate(storage["users"]):
        if user["id"] == user_id:
            storage["users"].pop(i)
            storage["categories"] = [c for c in storage["categories"] if c["user_id"] != user_id]
            storage["transactions"] = [t for t in storage["transactions"] if t["user_id"] != user_id]
            storage["budgets"] = [b for b in storage["budgets"] if b["user_id"] != user_id]
            storage["goals"] = [g for g in storage["goals"] if g["user_id"] != user_id]
            return True
    return False

def create_category(user_id: int, name: str, category_type: str) -> Dict[str, Any]:
    category = {
        "id": get_next_id("categories"),
        "user_id": user_id,
        "name": name,
        "type": category_type
    }
    storage["categories"].append(category)
    return category


def get_user_categories(user_id: int) -> List[Dict[str, Any]]:
    return [c for c in storage["categories"] if c["user_id"] == user_id]


def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
    for category in storage["categories"]:
        if category["id"] == category_id:
            return category
    return None

def create_transaction(user_id: int, category_id: int, amount: float, 
                       transaction_type: str, transaction_date: str, 
                       description: Optional[str] = None) -> Dict[str, Any]:
    transaction = {
        "id": get_next_id("transactions"),
        "user_id": user_id,
        "category_id": category_id,
        "amount": amount,
        "type": transaction_type,
        "transaction_date": transaction_date,
        "description": description,
        "created_at": datetime.utcnow()
    }
    storage["transactions"].append(transaction)
    return transaction


def get_user_transactions(user_id: int) -> List[Dict[str, Any]]:
    """Получить транзакции пользователя"""
    return [t for t in storage["transactions"] if t["user_id"] == user_id]


def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
    """Получить транзакцию по ID"""
    for transaction in storage["transactions"]:
        if transaction["id"] == transaction_id:
            return transaction
    return None


def delete_transaction(transaction_id: int) -> bool:
    """Удалить транзакцию"""
    for i, transaction in enumerate(storage["transactions"]):
        if transaction["id"] == transaction_id:
            storage["transactions"].pop(i)
            return True
    return False


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С БЮДЖЕТАМИ =====
def create_budget(user_id: int, category_id: int, limit_amount: float, period: str) -> Dict[str, Any]:
    """Создать бюджет"""
    budget = {
        "id": get_next_id("budgets"),
        "user_id": user_id,
        "category_id": category_id,
        "limit_amount": limit_amount,
        "period": period,
        "created_at": datetime.utcnow()
    }
    storage["budgets"].append(budget)
    return budget


def get_user_budgets(user_id: int) -> List[Dict[str, Any]]:
    """Получить бюджеты пользователя"""
    return [b for b in storage["budgets"] if b["user_id"] == user_id]


def delete_budget(budget_id: int) -> bool:
    """Удалить бюджет"""
    for i, budget in enumerate(storage["budgets"]):
        if budget["id"] == budget_id:
            storage["budgets"].pop(i)
            return True
    return False


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ЦЕЛЯМИ =====
def create_goal(user_id: int, name: str, target_amount: float, target_date: Optional[str] = None) -> Dict[str, Any]:
    """Создать финансовую цель"""
    goal = {
        "id": get_next_id("goals"),
        "user_id": user_id,
        "name": name,
        "target_amount": target_amount,
        "current_amount": 0.0,
        "target_date": target_date,
        "created_at": datetime.utcnow()
    }
    storage["goals"].append(goal)
    return goal


def get_user_goals(user_id: int) -> List[Dict[str, Any]]:
    """Получить цели пользователя"""
    return [g for g in storage["goals"] if g["user_id"] == user_id]


def get_goal_by_id(goal_id: int) -> Optional[Dict[str, Any]]:
    """Получить цель по ID"""
    for goal in storage["goals"]:
        if goal["id"] == goal_id:
            return goal
    return None


def contribute_to_goal(goal_id: int, amount: float) -> Optional[Dict[str, Any]]:
    """Пополнить финансовую цель"""
    goal = get_goal_by_id(goal_id)
    if not goal:
        return None
    goal["current_amount"] += amount
    return goal


def delete_goal(goal_id: int) -> bool:
    """Удалить финансовую цель"""
    for i, goal in enumerate(storage["goals"]):
        if goal["id"] == goal_id:
            storage["goals"].pop(i)
            return True
    return False


# ===== ИНИЦИАЛИЗАЦИЯ ТЕСТОВЫХ ДАННЫХ =====
def init_test_data():
    """Инициализировать тестовые данные"""
    # Создать тестового пользователя
    test_user = create_user(
        full_name="Иван Иванов",
        email="test@example.com",
        password="password123"
    )
    
    # Создать категории
    income_cat = create_category(test_user["id"], "Зарплата", "income")
    expense_cat1 = create_category(test_user["id"], "Продукты", "expense")
    expense_cat2 = create_category(test_user["id"], "Транспорт", "expense")
    
    # Создать транзакции
    create_transaction(test_user["id"], income_cat["id"], 50000.0, "income", "2024-01-15", "Зарплата за январь")
    create_transaction(test_user["id"], expense_cat1["id"], 5000.0, "expense", "2024-01-16", "Покупки в магазине")
    create_transaction(test_user["id"], expense_cat2["id"], 1500.0, "expense", "2024-01-17", "Проезд")
    
    # Создать бюджет
    create_budget(test_user["id"], expense_cat1["id"], 10000.0, "2024-01")
    
    # Создать цель
    create_goal(test_user["id"], "Отпуск", 100000.0, "2024-12-31")
    
    print("Тестовые данные загружены")

