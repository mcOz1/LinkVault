
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from authentication.services import auth_service, Token
from server import settings, session
import json
from server.limiter import limiter
from authentication.models import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register")
@limiter.limit("1/minute")
async def create_user(
    request: Request,
    session: session.SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    try:
        data = await auth_service.create_user(form_data.username, form_data.password, session=session)
        return Response(json.dumps(data).encode(), status_code=status.HTTP_201_CREATED)
    except Exception as e:
        await session.rollback()
        raise

@router.post("/token")
@limiter.limit("5/minute")
async def get_access_token(
    request: Request,
    session: session.SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await auth_service.authenticate_user(form_data.username, form_data.password, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return token

@router.get('/users')
@limiter.limit("1/second")
async def get_users(
    request: Request,
    session: session.SessionDep,
    current_user: User = Depends(auth_service.get_current_user)
    ):
    users = await auth_service.get_users(session=session)
    return users