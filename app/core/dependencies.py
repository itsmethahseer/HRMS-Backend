from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.modules.core_hr.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        schema_name: str = payload.get("schema_name")
        if user_id is None or schema_name is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_tenant_db_from_token(payload: dict = Depends(get_token_payload)) -> AsyncSession:
    schema_name = payload.get("schema_name")
    async with AsyncSessionLocal() as session:
        session.execution_options(schema_translate_map={None: schema_name})
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_tenant_db_from_token)
) -> User:
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
