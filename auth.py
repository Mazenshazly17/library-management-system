from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.user import (
    UserCreate, LoginRequest, TokenResponse, UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.user_service import UserService
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account. Default role is 'member'.",
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for email: {data.email}")
    user = UserService.register(db, data)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain JWT token",
    description="Authenticate with email and password to receive a Bearer token.",
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for email: {data.email}")
    result = UserService.authenticate(db, data.email, data.password)
    return result


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (client-side token invalidation)",
    description=(
        "JWT tokens are stateless. Logout is handled client-side by discarding the token. "
        "For production, implement a token blacklist with Redis."
    ),
)
def logout(current_user=Depends(get_current_user)):
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Logged out successfully. Please discard your token."}
