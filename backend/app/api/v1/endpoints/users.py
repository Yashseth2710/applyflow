"""Account and profile endpoints.

Separate from /auth, which is about getting in and out. This is about the
account once you are already in.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_storage
from app.api.v1.endpoints.auth import clear_session_cookies
from app.core.database import get_db
from app.core.storage import Storage
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.user import AccountDelete, PasswordChange, ProfileUpdate
from app.services.user import (
    IncorrectPassword,
    InvalidAvatar,
    SamePassword,
    UserService,
)

router = APIRouter()


def get_user_service(
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> UserService:
    """Storage arrives as a dependency so tests can point it somewhere else."""
    return UserService(db, storage)


def _with_avatar(user: User, service: UserService) -> UserResponse:
    """The picture is read from storage, so it is attached here rather than
    being a column the response model could pick up on its own."""
    response = UserResponse.model_validate(user)
    response.avatar = service.avatar_data_uri(user)
    return response


@router.get("/me", response_model=UserResponse, summary="The signed-in account")
def read_me(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return _with_avatar(current_user, service)


@router.patch("/me", response_model=UserResponse, summary="Update name and profile")
def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """One endpoint for the name and the profile fields, because on screen they
    are one form and a half-saved form is worse than a slow one."""
    user = service.update(current_user, payload)
    return _with_avatar(user, service)


@router.put("/me/avatar", response_model=UserResponse, summary="Set the profile picture")
def set_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Whatever arrives is decoded and re-encoded to a 256px WebP.

    That strips EXIF, which on a phone photo carries the coordinates it was
    taken at, and it is the only real check that the file is an image rather
    than something claiming to be one.
    """
    try:
        user = service.set_avatar(current_user, file.file, file.content_type)
    except InvalidAvatar as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return _with_avatar(user, service)


@router.delete("/me/avatar", response_model=UserResponse, summary="Go back to initials")
def clear_avatar(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = service.clear_avatar(current_user)
    return _with_avatar(user, service)


@router.post(
    "/me/password",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Change the password",
)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """Asks for the current password as well as a valid session — otherwise an
    unattended laptop is a way to take the account permanently."""
    try:
        service.change_password(
            current_user,
            current=payload.current_password,
            new=payload.new_password,
        )
    except IncorrectPassword as exc:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="That is not your current password.",
        ) from exc
    except SamePassword as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The new password is the same as the current one.",
        ) from exc


@router.delete("/me", status_code=http_status.HTTP_204_NO_CONTENT, summary="Delete the account")
def delete_me(
    payload: AccountDelete,
    response: Response,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """Irreversible, and takes everything with it.

    Every table cascades from `users`, including the stored file bytes, so one
    delete removes the applications, resumes, interviews and generated answers
    too. Nothing is retained.
    """
    try:
        service.delete_account(current_user, password=payload.password)
    except IncorrectPassword as exc:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="That is not your password.",
        ) from exc

    # The account is gone, so the refresh cookie can only produce 401s from
    # here. Clearing it server-side means the next page load does not try.
    clear_session_cookies(response)
