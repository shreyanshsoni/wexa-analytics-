from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbDep
from app.schemas.auth import (
    AuthData,
    InviteAcceptRequest,
    InviteInfoResponse,
    LoginRequest,
    OrgOut,
    SignupRequest,
    TokenData,
    UserOut,
)
from app.schemas.common import ApiResponse, MessageResponse
from app.services import auth_service

COOKIE_NAME = "refresh_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax")


@router.post("/signup", status_code=201)
async def signup(
    body: SignupRequest,
    response: Response,
    db: DbDep,
) -> ApiResponse[AuthData]:
    result = await auth_service.signup(
        session=db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        org_name=body.org_name,
    )
    _set_refresh_cookie(response, result.refresh_token_raw)
    return ApiResponse(
        data=AuthData(
            access_token=result.access_token,
            user=UserOut.model_validate(result.user),
            org=OrgOut.model_validate(result.org),
            role=result.role,
        )
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: DbDep,
) -> ApiResponse[AuthData]:
    result = await auth_service.login(
        session=db,
        email=body.email,
        password=body.password,
    )
    _set_refresh_cookie(response, result.refresh_token_raw)
    return ApiResponse(
        data=AuthData(
            access_token=result.access_token,
            user=UserOut.model_validate(result.user),
            org=OrgOut.model_validate(result.org),
            role=result.role,
        )
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: DbDep,
) -> ApiResponse[TokenData]:
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("No refresh token cookie")
    new_access = await auth_service.refresh_access_token(db, raw_token)
    return ApiResponse(data=TokenData(access_token=new_access))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: DbDep,
    _: CurrentUser,
) -> ApiResponse[MessageResponse]:
    raw_token = request.cookies.get(COOKIE_NAME)
    if raw_token:
        await auth_service.logout(db, raw_token)
    _clear_refresh_cookie(response)
    return ApiResponse(data=MessageResponse(message="Logged out successfully"))


@router.get("/invite/{token}")
async def get_invite_info(
    token: str,
    db: DbDep,
) -> ApiResponse[InviteInfoResponse]:
    info = await auth_service.get_invite_info(session=db, invite_token=token)
    return ApiResponse(data=InviteInfoResponse(**info))  # type: ignore[arg-type]


@router.post("/invite/{token}/accept", status_code=201)
async def accept_invite(
    token: str,
    body: InviteAcceptRequest,
    response: Response,
    db: DbDep,
) -> ApiResponse[AuthData]:
    result = await auth_service.accept_invite(
        session=db,
        invite_token=token,
        full_name=body.full_name,
        password=body.password,
    )
    _set_refresh_cookie(response, result.refresh_token_raw)
    return ApiResponse(
        data=AuthData(
            access_token=result.access_token,
            user=UserOut.model_validate(result.user),
            org=OrgOut.model_validate(result.org),
            role=result.role,
        )
    )


@router.get("/me")
async def get_me(current_user: CurrentUser) -> ApiResponse[UserOut]:
    return ApiResponse(data=UserOut.model_validate(current_user))
