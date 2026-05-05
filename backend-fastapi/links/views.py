
from fastapi import APIRouter, Depends, Request, Response, status
from server.limiter import limiter
from server import session
from authentication.models import User
from authentication.services import auth_service
from links.services import LinkService
from links.models import Link


router = APIRouter(
    prefix="/link",
    tags=["Links and Tags"]
)

@router.get("/create", response_model=Link, status_code=status.HTTP_201_CREATED)
@limiter.limit("1/second")
async def create_link(
    request: Request,
    session: session.SessionDep,
    link: str,
    current_user: User = Depends(auth_service.get_current_active_user),
):
    service = LinkService(session=session, user=current_user)
    data = await service.create_link(url=link)
    return data