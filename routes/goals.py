from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from models import (
    GoalCreate, Goal, GoalProgress, GoalContribute, 
    GoalUpdate, MessageResponse
)
from routes.auth import get_current_user
from utils import (
    create_goal, get_user_goals, get_goal_by_id,
    contribute_to_goal, delete_goal
)

router = APIRouter(prefix="/goals", tags=["Управление финансовыми целями"])

def calculate_goal_progress(goal: dict) -> GoalProgress:
    current_amount = goal.get("current_amount", 0.0)
    target_amount = goal["target_amount"]
    
    progress_percentage = (current_amount / target_amount * 100) if target_amount > 0 else 0
    
    remaining_amount = max(0, target_amount - current_amount)
    
    return GoalProgress(
        id=goal["id"],
        user_id=goal["user_id"],
        name=goal["name"],
        target_amount=goal["target_amount"],
        current_amount=current_amount,
        target_date=goal.get("target_date"),
        created_at=goal["created_at"],
        progress_percentage=round(progress_percentage, 2),
        remaining_amount=remaining_amount
    )


@router.post("/", response_model=GoalProgress, status_code=status.HTTP_201_CREATED)
async def create_financial_goal(
    goal_data: GoalCreate,
    current_user: dict = Depends(get_current_user)
):
    goal = create_goal(
        user_id=current_user["id"],
        name=goal_data.name,
        target_amount=goal_data.target_amount,
        target_date=str(goal_data.target_date) if goal_data.target_date else None
    )
    
    return calculate_goal_progress(goal)


@router.get("/progress", response_model=List[GoalProgress])
async def get_goals_progress(current_user: dict = Depends(get_current_user)):
    goals = get_user_goals(current_user["id"])
    
    goals_progress = []
    for goal in goals:
        progress = calculate_goal_progress(goal)
        goals_progress.append(progress)

    goals_progress.sort(key=lambda x: x.progress_percentage)
    
    return goals_progress


@router.get("/{goal_id}", response_model=GoalProgress)
async def get_goal_by_id_endpoint(
    goal_id: int,
    current_user: dict = Depends(get_current_user)
):
    goal = get_goal_by_id(goal_id)
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Финансовая цель не найдена"
        )
    
    if goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой цели"
        )
    
    return calculate_goal_progress(goal)


@router.post("/{goal_id}/contribute", response_model=GoalProgress)
async def contribute_to_financial_goal(
    goal_id: int,
    contribution: GoalContribute,
    current_user: dict = Depends(get_current_user)
):
    goal = get_goal_by_id(goal_id)
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Финансовая цель не найдена"
        )
    
    if goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой цели"
        )
    
    updated_goal = contribute_to_goal(goal_id, contribution.amount)
    
    if not updated_goal:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при пополнении цели"
        )
    
    return calculate_goal_progress(updated_goal)


@router.put("/{goal_id}", response_model=GoalProgress)
async def update_financial_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    current_user: dict = Depends(get_current_user)
):
    goal = get_goal_by_id(goal_id)
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Финансовая цель не найдена"
        )
    
    if goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой цели"
        )
    
    if goal_update.name is not None:
        goal["name"] = goal_update.name
    if goal_update.target_amount is not None:
        goal["target_amount"] = goal_update.target_amount
    if goal_update.target_date is not None:
        goal["target_date"] = str(goal_update.target_date)
    
    return calculate_goal_progress(goal)


@router.delete("/{goal_id}", response_model=MessageResponse)
async def delete_financial_goal(
    goal_id: int,
    current_user: dict = Depends(get_current_user)
):
    goal = get_goal_by_id(goal_id)
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Финансовая цель не найдена"
        )
    
    if goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой цели"
        )
    
    success = delete_goal(goal_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении цели"
        )
    
    return MessageResponse(
        message="Финансовая цель успешно удалена",
        detail=f"Цель '{goal['name']}' была удалена"
    )

