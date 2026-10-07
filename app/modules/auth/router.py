from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError

from app.db.session import get_db, AsyncSessionLocal
from app.db.public_models import Tenant
from app.modules.core_hr.models import User
from app.modules.auth import schemas
from app.core import security
from app.core.config import settings

from app.core.dependencies import get_current_user, get_tenant_db_from_token, oauth2_scheme
from app.modules.core_hr import schemas as core_schemas

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# HELPER: open tenant-scoped session by schema name
# ─────────────────────────────────────────────────────────────
async def _get_tenant_session(schema_name: str):
    import app.db.session as sess_module
    cur_engine = sess_module.engine
    is_postgres = "postgresql" in str(cur_engine.url)
    opts = {"schema_translate_map": {None: schema_name}} if is_postgres else {}
    bind_engine = cur_engine.execution_options(**opts) if opts else cur_engine
    return sess_module.AsyncSessionLocal(bind=bind_engine)


# ─────────────────────────────────────────────────────────────
# GET /me
# ─────────────────────────────────────────────────────────────
@router.get("/me", response_model=core_schemas.User, summary="Get currently logged-in user")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db_from_token)
):
    """Returns the currently authenticated user's data."""
    return current_user


# ─────────────────────────────────────────────────────────────
# POST /login
# ─────────────────────────────────────────────────────────────
@router.post("/login", response_model=schemas.Token, summary="Employee Login")
async def login(credentials: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Find the company (Tenant) in the public schema
    result = await db.execute(select(Tenant).where(Tenant.company_name == credentials.company_name))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=400, detail="Company not found")

    # 2. Open a NEW database session pointed at this company's schema
    import app.db.session as sess_module
    cur_engine = sess_module.engine
    is_postgres = "postgresql" in str(cur_engine.url)
    opts = {"schema_translate_map": {None: tenant.schema_name}} if is_postgres else {}
    bind_engine = cur_engine.execution_options(**opts) if opts else cur_engine
    async with sess_module.AsyncSessionLocal(bind=bind_engine) as tenant_db:
        user_result = await tenant_db.execute(select(User).where(User.email == credentials.email))
        user = user_result.scalars().first()
        
        if not user or not security.verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Generate JWT Token
    token_data = {
        "sub": str(user.id),
        "schema_name": tenant.schema_name,
        "is_superuser": user.is_superuser,
        "email": user.email,
    }
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(data=token_data, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "schema_name": tenant.schema_name,
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
    }


# ─────────────────────────────────────────────────────────────
# POST /refresh  — exchange a valid token for a new one
# ─────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=schemas.Token, summary="Refresh Access Token")
async def refresh_token(token: str = Depends(oauth2_scheme)):
    """
    Pass your current access token (still valid or just-expired by a grace period).
    Returns a brand-new access token with the same claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},  # allow slightly expired tokens
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token for refresh")

    schema_name: str = payload.get("schema_name")
    user_id: str = payload.get("sub")
    if not schema_name or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Look up user to ensure still active
    async with (await _get_tenant_session(schema_name)) as tenant_db:
        result = await tenant_db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

    # Blacklist old token and issue fresh one
    security.blacklist_token(token)
    token_data = {
        "sub": str(user.id),
        "schema_name": schema_name,
        "is_superuser": user.is_superuser,
        "email": user.email,
    }
    new_token = security.create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "schema_name": schema_name,
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
    }


# ─────────────────────────────────────────────────────────────
# POST /logout  — blacklist current token
# ─────────────────────────────────────────────────────────────
@router.post("/logout", summary="Logout (Revoke Token)")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user)
):
    """Invalidates the current JWT token. Use Redis in production."""
    security.blacklist_token(token)
    return {"detail": "Successfully logged out"}


# ─────────────────────────────────────────────────────────────
# POST /change-password  — for logged-in users
# ─────────────────────────────────────────────────────────────
@router.post("/change-password", summary="Change Password (Authenticated)")
async def change_password(
    data: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db_from_token)
):
    """Allows a logged-in user to change their own password."""
    if not security.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = security.get_password_hash(data.new_password)
    await db.commit()
    return {"detail": "Password changed successfully"}


# ─────────────────────────────────────────────────────────────
# POST /forgot-password  — generate a reset token
# ─────────────────────────────────────────────────────────────
@router.post("/forgot-password", summary="Request Password Reset Link")
async def forgot_password(
    data: schemas.ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Looks up the user and generates a password reset token.
    In production, send this token via email. Here, it is returned in the response for testing.
    """
    # Find tenant
    result = await db.execute(select(Tenant).where(Tenant.company_name == data.company_name))
    tenant = result.scalars().first()
    if not tenant:
        # Return generic message to prevent user enumeration
        return {"detail": "If your email exists, a reset link will be sent."}

    async with (await _get_tenant_session(tenant.schema_name)) as tenant_db:
        user_result = await tenant_db.execute(select(User).where(User.email == data.email))
        user = user_result.scalars().first()

    if not user:
        return {"detail": "If your email exists, a reset link will be sent."}

    reset_token = security.generate_password_reset_token(tenant.schema_name, user.id)
    # In production: send email with reset_token
    return {
        "detail": "Password reset token generated. In production, this would be emailed.",
        "reset_token": reset_token  # Only exposed for development/testing
    }


# ─────────────────────────────────────────────────────────────
# POST /reset-password  — consume token and set new password
# ─────────────────────────────────────────────────────────────
@router.post("/reset-password", summary="Reset Password Using Token")
async def reset_password(data: schemas.ResetPasswordRequest):
    """Consumes the password reset token and sets a new password."""
    token_data = security.verify_password_reset_token(data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    schema_name = token_data["schema_name"]
    user_id = token_data["user_id"]

    async with (await _get_tenant_session(schema_name)) as tenant_db:
        result = await tenant_db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = security.get_password_hash(data.new_password)
        await tenant_db.commit()

    security.consume_password_reset_token(data.token)
    return {"detail": "Password has been reset successfully. Please login with your new password."}
