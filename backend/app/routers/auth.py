from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import User, Role
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    # 1. Check whether the email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 2. Find the VIEWER role
    viewer_role = (
        db.query(Role)
        .filter(Role.role_name == "VIEWER")
        .first()
    )

    if not viewer_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VIEWER role not found"
        )

    # 3. Hash the password
    hashed_password = hash_password(user_data.password)

    # 4. Create the user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        phone=user_data.phone,
        role_id=viewer_role.role_id,
        is_active=True
    )

    # 5. Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ADD LOGIN BELOW REGISTER
@router.post("/login")
def login(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):
    # 1. Find the user by email
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    # 2. Check email
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 3. Check password
    if not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 4. Check whether account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # 5. Login successful
    access_token = create_access_token(user.user_id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
        } 
@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user