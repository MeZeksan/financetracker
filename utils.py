from passlib.context import CryptContext
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from db import SessionLocal, User, Category, Transaction, Budget, Goal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def user_to_dict(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "password": user.password,
        "created_at": user.created_at
    }


def category_to_dict(category: Category) -> Dict[str, Any]:
    return {
        "id": category.id,
        "user_id": category.user_id,
        "name": category.name,
        "type": category.type
    }


def transaction_to_dict(transaction: Transaction) -> Dict[str, Any]:
    return {
        "id": transaction.id,
        "user_id": transaction.user_id,
        "category_id": transaction.category_id,
        "amount": transaction.amount,
        "type": transaction.type,
        "transaction_date": transaction.transaction_date,
        "description": transaction.description,
        "created_at": transaction.created_at
    }


def budget_to_dict(budget: Budget) -> Dict[str, Any]:
    return {
        "id": budget.id,
        "user_id": budget.user_id,
        "category_id": budget.category_id,
        "limit_amount": budget.limit_amount,
        "period": budget.period,
        "created_at": budget.created_at
    }


def goal_to_dict(goal: Goal) -> Dict[str, Any]:
    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "name": goal.name,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "target_date": goal.target_date,
        "created_at": goal.created_at
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user_to_dict(user)
        return None
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user_to_dict(user)
        return None
    finally:
        db.close()


def create_user(full_name: str, email: str, password: str) -> Dict[str, Any]:
    db = get_db()
    try:
        user = User(
            full_name=full_name,
            email=email,
            password=get_password_hash(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_dict(user)
    finally:
        db.close()


def update_user(user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if "password" in kwargs and kwargs["password"]:
            user.password = get_password_hash(kwargs["password"])
            kwargs.pop("password")
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        return user_to_dict(user)
    finally:
        db.close()


def delete_user(user_id: int) -> bool:
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True
    finally:
        db.close()


def create_category(user_id: int, name: str, category_type: str) -> Dict[str, Any]:
    db = get_db()
    try:
        category = Category(
            user_id=user_id,
            name=name,
            type=category_type
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category_to_dict(category)
    finally:
        db.close()


def get_user_categories(user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        categories = db.query(Category).filter(Category.user_id == user_id).all()
        return [category_to_dict(cat) for cat in categories]
    finally:
        db.close()


def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category:
            return category_to_dict(category)
        return None
    finally:
        db.close()


def update_category(category_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return None
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(category, key, value)
        
        db.commit()
        db.refresh(category)
        return category_to_dict(category)
    finally:
        db.close()


def delete_category(category_id: int) -> bool:
    db = get_db()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return False
        db.delete(category)
        db.commit()
        return True
    finally:
        db.close()


def create_transaction(user_id: int, category_id: int, amount: float, 
                       transaction_type: str, transaction_date: str, 
                       description: Optional[str] = None) -> Dict[str, Any]:
    db = get_db()
    try:
        transaction = Transaction(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            type=transaction_type,
            transaction_date=transaction_date,
            description=description
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction_to_dict(transaction)
    finally:
        db.close()


def get_user_transactions(user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
        return [transaction_to_dict(t) for t in transactions]
    finally:
        db.close()


def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            return transaction_to_dict(transaction)
        return None
    finally:
        db.close()


def delete_transaction(transaction_id: int) -> bool:
    db = get_db()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return False
        db.delete(transaction)
        db.commit()
        return True
    finally:
        db.close()


def create_budget(user_id: int, category_id: int, limit_amount: float, period: str) -> Dict[str, Any]:
    db = get_db()
    try:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            limit_amount=limit_amount,
            period=period
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return budget_to_dict(budget)
    finally:
        db.close()


def get_user_budgets(user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
        return [budget_to_dict(b) for b in budgets]
    finally:
        db.close()


def update_budget(budget_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            return None
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(budget, key, value)
        
        db.commit()
        db.refresh(budget)
        return budget_to_dict(budget)
    finally:
        db.close()


def delete_budget(budget_id: int) -> bool:
    db = get_db()
    try:
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            return False
        db.delete(budget)
        db.commit()
        return True
    finally:
        db.close()


def create_goal(user_id: int, name: str, target_amount: float, target_date: Optional[str] = None) -> Dict[str, Any]:
    db = get_db()
    try:
        goal = Goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=0.0,
            target_date=target_date
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal_to_dict(goal)
    finally:
        db.close()


def get_user_goals(user_id: int) -> List[Dict[str, Any]]:
    db = get_db()
    try:
        goals = db.query(Goal).filter(Goal.user_id == user_id).all()
        return [goal_to_dict(g) for g in goals]
    finally:
        db.close()


def get_goal_by_id(goal_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if goal:
            return goal_to_dict(goal)
        return None
    finally:
        db.close()


def contribute_to_goal(goal_id: int, amount: float) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return None
        goal.current_amount += amount
        db.commit()
        db.refresh(goal)
        return goal_to_dict(goal)
    finally:
        db.close()


def update_goal(goal_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    db = get_db()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return None
        
        for key, value in kwargs.items():
            if value is not None:
                if key == "target_date":
                    setattr(goal, key, str(value))
                else:
                    setattr(goal, key, value)
        
        db.commit()
        db.refresh(goal)
        return goal_to_dict(goal)
    finally:
        db.close()


def delete_goal(goal_id: int) -> bool:
    db = get_db()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return False
        db.delete(goal)
        db.commit()
        return True
    finally:
        db.close()


def init_test_data():
    db = get_db()
    try:
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            return
        
        test_user = User(
            full_name="Иван Иванов",
            email="test@example.com",
            password=get_password_hash("password123")
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        income_cat = Category(
            user_id=test_user.id,
            name="Зарплата",
            type="income"
        )
        expense_cat1 = Category(
            user_id=test_user.id,
            name="Продукты",
            type="expense"
        )
        expense_cat2 = Category(
            user_id=test_user.id,
            name="Транспорт",
            type="expense"
        )
        db.add_all([income_cat, expense_cat1, expense_cat2])
        db.commit()
        db.refresh(income_cat)
        db.refresh(expense_cat1)
        db.refresh(expense_cat2)
        
        transaction1 = Transaction(
            user_id=test_user.id,
            category_id=income_cat.id,
            amount=50000.0,
            type="income",
            transaction_date="2024-01-15",
            description="Зарплата за январь"
        )
        transaction2 = Transaction(
            user_id=test_user.id,
            category_id=expense_cat1.id,
            amount=5000.0,
            type="expense",
            transaction_date="2024-01-16",
            description="Покупки в магазине"
        )
        transaction3 = Transaction(
            user_id=test_user.id,
            category_id=expense_cat2.id,
            amount=1500.0,
            type="expense",
            transaction_date="2024-01-17",
            description="Проезд"
        )
        db.add_all([transaction1, transaction2, transaction3])
        db.commit()
        
        budget = Budget(
            user_id=test_user.id,
            category_id=expense_cat1.id,
            limit_amount=10000.0,
            period="2024-01"
        )
        db.add(budget)
        db.commit()
        
        goal = Goal(
            user_id=test_user.id,
            name="Отпуск",
            target_amount=100000.0,
            target_date="2024-12-31"
        )
        db.add(goal)
        db.commit()
        
        print("Тестовые данные загружены")
    finally:
        db.close()
