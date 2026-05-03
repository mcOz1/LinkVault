from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlmodel import select
from server import settings, session
from authentication.models import User


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthService:
    password_hash = PasswordHash.recommended()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

    def verify_password(self, plain_password, hashed_password):
        return self.password_hash.verify(plain_password, hashed_password)


    def get_password_hash(self, password):
        return self.password_hash.hash(password)


    async def get_user_or_404(self, username: str, session: session.SessionDep) -> User:
        user = await session.scalar(select(User).where(User.username == username))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user


    async def get_user_or_none(self, username: str, session: session.SessionDep) -> User | None:
        user = await session.scalar(select(User).where(User.username == username))
        if not user:
            return None
        return user
    
    async def create_user(self, username: str, password: str, session: session.SessionDep):
        hashed_password = self.get_password_hash(password)
        user = User(username=username, hashed_password=hashed_password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = self.create_access_token({"sub": user.username})
        return {
            "access_token": token.access_token,
            "token_type": token.token_type,
        }

    async def authenticate_user(self, username: str, password: str, session:session.SessionDep):
        user = await self.get_user_or_none(username, session=session)
        if not user:
            return False
        if not self.verify_password(password, user.hashed_password):
            return False
        return user


    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return Token(access_token=encoded_jwt, token_type="bearer")


    async def get_current_user(self, token: Annotated[str, Depends(oauth2_scheme)], session: session.SessionDep):
        payload = self.verify_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self.get_user_or_none(username=username, session=session)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deleted",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


    async def get_current_active_user(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
    ):
        if not current_user.active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    async def get_users(
        self,
        session: session.SessionDep,
        offset: int = 0,
        limit: Annotated[int, Query(le=100)] = 100,
    ):
        result = await session.scalars(select(User).offset(offset).limit(limit))
        return result.all()

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
auth_service = AuthService()