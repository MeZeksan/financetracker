from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from routes import auth, transaction, budget, goals, analytics
from utils import init_test_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("FinanceTracker API запущен!")
    print("=" * 60)
    print("Документация Swagger: http://localhost:8000/docs")
    print("Документация ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    print("Инициализация тестовых данных...")
    init_test_data()
    print("=" * 60)
    print("Готов к работе!")
    print("=" * 60)
    yield
    print("Остановка приложения...")

app = FastAPI(
    lifespan=lifespan,
    title="FinanceTracker API",
    description="""
    # FinanceTracker - Менеджер персональных финансов
    
    Сервис для управления личными финансами, учета доходов и расходов, 
    планирования бюджета и анализа финансового состояния.
    
    ## Основные возможности:
    
    * **Управление учетной записью** - регистрация, авторизация, редактирование профиля
    * **Управление транзакциями** - добавление доходов и расходов, просмотр истории
    * **Управление бюджетом** - установка лимитов расходов, отслеживание выполнения
    * **Финансовые цели** - постановка целей накопления, отслеживание прогресса
    * **Аналитика** - статистика по категориям, динамика расходов
    
    ## Авторизация:
    
    Авторизация работает через сессии. Для работы с API:
    
    1. Зарегистрируйтесь через `/auth/register` или войдите через `/auth/login`
    2. После успешного входа сессия сохраняется автоматически
    3. Все последующие запросы будут использовать эту сессию
    4. Для выхода используйте `/auth/logout`
    
    ## Тестовые данные:
    
    При запуске приложения автоматически создается тестовый пользователь:
    - **Email**: test@example.com
    - **Пароль**: password123
    """,
    version="1.0.0",
    contact={
        "name": "FinanceTracker Support",
        "email": "support@financetracker.com"
    }
)

app.add_middleware(
    SessionMiddleware,
    secret_key="secret-key-for-sessions"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transaction.router)
app.include_router(budget.router)
app.include_router(goals.router)
app.include_router(analytics.router)


@app.get("/", tags=["Главная"])
async def root():
    return {
        "message": "Добро пожаловать в FinanceTracker API!",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "auth": "/auth",
            "transactions": "/transactions",
            "budgets": "/budgets",
            "goals": "/goals",
            "analytics": "/analytics"
        },
        "test_user": {
            "email": "test@example.com",
            "password": "password123",
            "note": "Используйте эти данные для входа и тестирования API"
        }
    }


@app.get("/health", tags=["Главная"])
async def health_check():
    return {
        "status": "healthy",
        "service": "FinanceTracker API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

