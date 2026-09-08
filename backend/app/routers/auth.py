from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


from app.database.connection import get_db
from app.models import Accident, AuthOTP, AuditLog, EmergencyResponse, User, Role
from app.email import EmailDeliveryError, send_email_verification_otp, send_password_reset_otp
from app.schemas.auth import (
    RegisterRequest,
    UserUpdateRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    create_otp,
    hash_otp,
    verify_otp
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
            detail="An account with this email is already registered. Please log in, or use forgot password if you need to recover your account."
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
        is_active=True,
        is_email_verified=False
    )

    # 5. Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    otp = create_otp()
    db.add(AuthOTP(
        user_id=new_user.user_id,
        purpose="email_verification",
        otp_hash=hash_otp(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        created_at=datetime.now(timezone.utc)
    ))
    db.commit()

    try:
        send_email_verification_otp(str(new_user.email), otp)
    except EmailDeliveryError:
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send email verification code"
        )

    return new_user


# ADD LOGIN BELOW REGISTER
@router.post("/login", response_model=LoginResponse)
def login(
    user_data: LoginRequest,
    request: Request,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wrong email address."
        )

    # 3. Check password
    if not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong password."
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email is not verified yet. Please verify your email using the OTP sent to your inbox before logging in."
        )

    # 4. Check whether account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact support or administrator for assistance."
        )

    # 5. Login successful
    login_at = datetime.now(timezone.utc)
    access_token = create_access_token(user.user_id)
    db.add(AuditLog(
        user_id=user.user_id,
        action="LOGIN",
        entity_type="authentication",
        entity_id=user.user_id,
        timestamp=login_at,
        ip_address=request.client.host if request.client else None,
        details="User logged in successfully"
    ))
    db.commit()

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "login_at": login_at,
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role_id": user.role_id,
            "role_name": user.role.role_name if user.role else None,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
        }
    }


@router.post("/verify-email")
def verify_email(
    verification_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == verification_data.email).first()
    otp_record = None
    if user:
        otp_record = (
            db.query(AuthOTP)
            .filter(
                AuthOTP.user_id == user.user_id,
                AuthOTP.purpose == "email_verification"
            )
            .order_by(AuthOTP.created_at.desc())
            .first()
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address. Please register first."
        )

    if user.is_email_verified:
        return {"message": "Email is already verified. Please proceed to login."}

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending email verification OTP found for this account. Please request a new verification code."
        )

    if otp_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new verification code."
        )

    if not verify_otp(verification_data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect verification code. Please check the OTP sent to your email and try again."
        )

    user.is_email_verified = True
    db.delete(otp_record)
    db.commit()

    return {"message": "Email verified successfully"}


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    user_id: UUID = Depends(get_current_user),
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


@router.put(
    "/me",
    response_model=UserResponse
)
def update_me(
    user_data: UserUpdateRequest,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.user_id == user_id, User.is_active.is_(True))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updates = user_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required"
        )

    if "email" in updates:
        existing_user = (
            db.query(User)
            .filter(User.email == updates["email"], User.user_id != user_id)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    if "password" in updates:
        user.password_hash = hash_password(updates.pop("password"))

    for field, value in updates.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.delete("/me")
def delete_me(
    request: Request,
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.user_id == user_id, User.is_active.is_(True))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    deleted_at = datetime.now(timezone.utc)
    db.query(AuthOTP).filter(AuthOTP.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(Accident).filter(Accident.created_by == user_id).update(
        {Accident.created_by: None},
        synchronize_session=False
    )
    db.query(EmergencyResponse).filter(
        EmergencyResponse.assigned_user_id == user_id
    ).update(
        {EmergencyResponse.assigned_user_id: None},
        synchronize_session=False
    )
    db.add(AuditLog(
        user_id=None,
        action="DELETE",
        entity_type="user",
        entity_id=user_id,
        timestamp=deleted_at,
        ip_address=request.client.host if request.client else None,
        details="User permanently deleted their own account"
    ))
    db.delete(user)
    db.commit()

    return {
        "message": "User account deleted successfully",
        "deleted_at": deleted_at
    }


@router.post("/forgot-password")
def forgot_password(
    user_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email, User.is_active.is_(True))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account found with this email. Please register before requesting a password reset."
        )

    otp = create_otp()
    db.query(AuthOTP).filter(
        AuthOTP.user_id == user.user_id,
        AuthOTP.purpose == "password_reset"
    ).delete(synchronize_session=False)
    db.add(AuthOTP(
        user_id=user.user_id,
        purpose="password_reset",
        otp_hash=hash_otp(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        created_at=datetime.now(timezone.utc)
    ))
    db.commit()

    try:
        send_password_reset_otp(str(user.email), otp)
    except EmailDeliveryError:
        db.query(AuthOTP).filter(
            AuthOTP.user_id == user.user_id,
            AuthOTP.purpose == "password_reset"
        ).delete(synchronize_session=False)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send password reset email"
        )

    return {
        "message": "If that email is registered, an OTP has been sent"
    }


@router.post("/reset-password")
def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == reset_data.email, User.is_active.is_(True))
        .first()
    )

    otp_record = None
    if user:
        otp_record = (
            db.query(AuthOTP)
            .filter(
                AuthOTP.user_id == user.user_id,
                AuthOTP.purpose == "password_reset"
            )
            .order_by(AuthOTP.created_at.desc())
            .first()
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active account found with this email address. Please register first."
        )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password reset request found for this email. Please request a reset code using forgot-password first."
        )

    if otp_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset code has expired. Please request a new reset OTP."
        )

    if not verify_otp(reset_data.otp, otp_record.otp_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password reset code. Please check the OTP sent to your email and try again."
        )

    user.password_hash = hash_password(reset_data.new_password)
    db.delete(otp_record)
    db.commit()

    return {
        "message": "Password reset successful"
    }
