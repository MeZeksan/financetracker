from fastapi import APIRouter, HTTPException, Depends, Header, status
from typing import Optional
from models import (
    UserCreate, UserLogin, UserUpdate, UserResponse, 
    TokenResponse, MessageResponse
)
from utils import (
    get_user_by_email, get_user_by_id, create_user, update_user, 
    delete_user, verify_password, create_access_token, decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Управление учетной записью"])


# ===== ЗАВИСИМОСТЬ ДЛЯ ПОЛУЧЕНИЯ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ =====
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Получить текущего пользователя из токена"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверная схема авторизации"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат токена"
        )
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )
    
    user_id = payload.get("user_id")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Регистрация нового пользователя
    
    - **full_name**: ФИО пользователя
    - **email**: Email пользователя (должен быть уникальным)
    - **password**: Пароль (минимум 6 символов)
    """
    # Проверить, существует ли пользователь с таким email
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Создать пользователя
    user = create_user(
        full_name=user_data.full_name,
        email=user_data.email,
        password=user_data.password
    )
    
    # Создать токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            full_name=user["full_name"],
            email=user["email"],
            created_at=user["created_at"]
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Авторизация пользователя
    
    - **email**: Email пользователя
    - **password**: Пароль пользователя
    """
    # Найти пользователя
    user = get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    # Проверить пароль
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    # Создать токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            full_name=user["full_name"],
            email=user["email"],
            created_at=user["created_at"]
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Получить информацию о текущем пользователе
    
    Требуется авторизация через Bearer токен в заголовке Authorization
    """
    return UserResponse(
        id=current_user["id"],
        full_name=current_user["full_name"],
        email=current_user["email"],
        created_at=current_user["created_at"]
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Изменить данные текущего пользователя
    
    - **full_name**: Новое ФИО (опционально)
    - **email**: Новый email (опционально)
    - **password**: Новый пароль (опционально, минимум 6 символов)
    
    Требуется авторизация через Bearer токен
    """
    # Если меняется email, проверить уникальность
    if user_update.email and user_update.email != current_user["email"]:
        existing_user = get_user_by_email(user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
    
    # Обновить данные
    updated_user = update_user(
        current_user["id"],
        full_name=user_update.full_name,
        email=user_update.email,
        password=user_update.password
    )
    
    return UserResponse(
        id=updated_user["id"],
        full_name=updated_user["full_name"],
        email=updated_user["email"],
        created_at=updated_user["created_at"]
    )


@router.delete("/me", response_model=MessageResponse)
async def delete_current_user(current_user: dict = Depends(get_current_user)):
    """
    Удалить учетную запись текущего пользователя
    
    Это действие удалит все связанные данные (транзакции, бюджеты, цели и т.д.)
    
    Требуется авторизация через Bearer токен
    """
    success = delete_user(current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении пользователя"
        )
    
    return MessageResponse(
        message="Учетная запись успешно удалена",
        detail="Все связанные данные также были удалены"
    )

