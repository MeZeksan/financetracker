from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class CategoryType(str, Enum):
    income = "income"
    expense = "expense"

class UserBase(BaseModel):
    full_name: str = Field(..., description="ФИО пользователя")
    email: EmailStr = Field(..., description="Email пользователя")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="ФИО пользователя")
    email: Optional[EmailStr] = Field(None, description="Email пользователя")
    password: Optional[str] = Field(None, min_length=6, description="Новый пароль")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime

class CategoryBase(BaseModel):
    name: str = Field(..., description="Название категории")
    type: CategoryType = Field(..., description="Тип категории")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Название категории")
    type: Optional[CategoryType] = Field(None, description="Тип категории")

class Category(CategoryBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    category_id: int = Field(..., description="ID категории")
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    type: TransactionType = Field(..., description="Тип транзакции")
    transaction_date: date = Field(..., description="Дата транзакции")
    description: Optional[str] = Field(None, description="Описание транзакции")

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionResponse(Transaction):
    category_name: Optional[str] = None

class BudgetBase(BaseModel):
    category_id: int = Field(..., description="ID категории")
    limit_amount: float = Field(..., gt=0, description="Лимит суммы")
    period: str = Field(..., description="Период (например: 2024-01)")

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    category_id: Optional[int] = Field(None, description="ID категории")
    limit_amount: Optional[float] = Field(None, gt=0, description="Лимит суммы")
    period: Optional[str] = Field(None, description="Период (например: 2024-01)")


class BudgetTopUp(BaseModel):
    amount: float = Field(..., gt=0, description="На сколько увеличить лимит")


class BudgetSpend(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма расхода")
    description: Optional[str] = Field(None, description="Описание операции")
    transaction_date: Optional[date] = Field(
        None,
        description="Дата расхода YYYY-MM-DD (должна попадать в период бюджета; иначе будет подставлена дата по умолчанию)",
    )

class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class BudgetStatus(Budget):
    category_name: str
    spent_amount: float
    remaining_amount: float
    percentage_used: float

class GoalBase(BaseModel):
    name: str = Field(..., description="Название цели")
    target_amount: float = Field(..., gt=0, description="Целевая сумма")
    target_date: Optional[date] = Field(None, description="Дата достижения цели")

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = Field(None, gt=0)
    target_date: Optional[date] = None

class GoalContribute(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма пополнения")

class Goal(GoalBase):
    id: int
    user_id: int
    current_amount: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True

class GoalProgress(Goal):
    progress_percentage: float
    remaining_amount: float

class CategoryStatistics(BaseModel):
    category_name: str
    category_id: int
    total_amount: float
    transaction_count: int
    percentage: float

class PeriodStatistics(BaseModel):
    period: str
    total_income: float
    total_expense: float
    balance: float
    categories: List[CategoryStatistics]

class ExpenseDynamics(BaseModel):
    date: str
    amount: float

class AnalyticsResponse(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    expense_by_category: List[CategoryStatistics]
    income_by_category: List[CategoryStatistics]
    expense_dynamics: List[ExpenseDynamics]

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class AIForecastResponse(BaseModel):
    id: int
    period: str
    forecasted_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


class AIAnomalyResponse(BaseModel):
    id: int
    transaction_id: int
    anomaly_score: float
    reason: Optional[str] = None
    detected_at: datetime
    amount: float
    transaction_date: str
    description: Optional[str] = None
    category_name: str
    category_id: int
    transaction_type: str

    class Config:
        from_attributes = True


class AIBudgetRecommendationResponse(BaseModel):
    id: int
    category_id: int
    category_name: Optional[str] = None
    recommendation_type: str
    current_limit: Optional[float] = None
    proposed_limit: Optional[float] = None
    justification: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyItem(BaseModel):
    transaction_id: int
    amount: float
    transaction_date: str
    category_name: str
    transaction_type: str
    description: Optional[str] = None
    anomaly_score: float
    reason: Optional[str] = None


class AnomalyDetectionResult(BaseModel):
    detected: int
    total_analyzed: int
    anomalies: List[AnomalyItem]
    message: str


class ForecastPeriod(BaseModel):
    period: str
    forecasted_balance: float


class ForecastResult(BaseModel):
    periods: int
    based_on_months: int
    avg_monthly_income: float
    avg_monthly_expense: float
    monthly_trend: float
    forecasts: List[ForecastPeriod]
    message: str


class RecommendationItem(BaseModel):
    category_name: str
    recommendation_type: str
    current_limit: Optional[float] = None
    proposed_limit: Optional[float] = None
    justification: Optional[str] = None


class RecommendationsResult(BaseModel):
    recommendations_created: int
    analysis_periods: List[str]
    items: List[RecommendationItem]
    message: str


class AnalyzeAllResult(BaseModel):
    anomaly_detection: AnomalyDetectionResult
    forecast: ForecastResult
    recommendations: RecommendationsResult
