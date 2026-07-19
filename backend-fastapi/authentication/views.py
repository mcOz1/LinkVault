from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from authentication.services import auth_service, get_current_active_user
from server import settings, session
import json
from server.limiter import limiter
from authentication.models import User
from authentication.constants import TokenType

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
@limiter.limit("1/minute")
async def create_user(
    request: Request,
    session: session.SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    try:
        data = await auth_service.create_user(
            form_data.username, form_data.password, session=session
        )
        return Response(json.dumps(data).encode(), status_code=status.HTTP_201_CREATED)
    except Exception as e:
        print(e)
        await session.rollback()
        raise


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    session: session.SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = await auth_service.authenticate_user(
        form_data.username, form_data.password, session=session
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    refresh_token = await auth_service.create_refresh_token(data={"sub": user.username})
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=max_age,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users", response_model=list[User])
@limiter.limit("1/second")
async def get_users(
    request: Request,
    session: session.SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    users = await auth_service.get_users(session=session)
    return users


@router.post("/refresh-token")
@limiter.limit("5/second")
async def refresh_access_token(
    request: Request,
    session: session.SessionDep,
) -> dict[str, str]:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_data = auth_service.verify_token(
        token=refresh_token, expected_token_type=TokenType.REFRESH
    )
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = auth_service.create_access_token({"sub": user_data.get("sub")})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: session.SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    response.delete_cookie(key="refresh_token")
    return {"message": "Logout successful"}
