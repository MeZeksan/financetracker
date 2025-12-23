from fastapi import APIRouter, HTTPException, Request, status
from models import (
    UserCreate, UserLogin, UserUpdate, UserResponse, 
    MessageResponse
)
from utils import (
    get_user_by_email, get_user_by_id, create_user, update_user, 
    delete_user, verify_password
)

router = APIRouter(prefix="/auth", tags=["Управление учетной записью"])


async def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request):
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    user = create_user(
        full_name=user_data.full_name,
        email=user_data.email,
        password=user_data.password
    )
    
    request.session["user_id"] = user["id"]
    
    return UserResponse(
        id=user["id"],
        full_name=user["full_name"],
        email=user["email"],
        created_at=user["created_at"]
    )


@router.post("/login", response_model=UserResponse)
async def login(credentials: UserLogin, request: Request):
    user = get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    request.session["user_id"] = user["id"]
    
    return UserResponse(
        id=user["id"],
        full_name=user["full_name"],
        email=user["email"],
        created_at=user["created_at"]
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request):
    request.session.clear()
    return MessageResponse(
        message="Вы успешно вышли из системы"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return UserResponse(
        id=user["id"],
        full_name=user["full_name"],
        email=user["email"],
        created_at=user["created_at"]
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    current_user = get_user_by_id(user_id)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    if user_update.email and user_update.email != current_user["email"]:
        existing_user = get_user_by_email(user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
    
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
async def delete_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    success = delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении пользователя"
        )
    
    request.session.clear()
    
    return MessageResponse(
        message="Учетная запись успешно удалена",
        detail="Все связанные данные также были удалены"
    )

