"""Authentication module for the API.

This module provides functions for authenticating users and managing JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.db.database import get_db
from src.api.v1.user.models import User, UserDB

# Router for authentication endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Secret key for JWT token signing
# In production, this should be stored securely (e.g., environment variable)
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model for decoded JWT."""

    username: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model."""

    email: str
    password: str


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password.

    Args:
        db: SQLAlchemy database session
        email: User email
        password: User password (plain text)

    Returns:
        User object if authentication successful, None otherwise

    """
    user_db = db.query(UserDB).filter(UserDB.email == email).first()
    if not user_db:
        return None

    user = User.model_validate(user_db)
    if not user.validate_password(password, user_db.password):
        return None

    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time delta

    Returns:
        Encoded JWT token

    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Get the current user from the JWT token.

    Args:
        token: JWT token
        db: SQLAlchemy database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found

    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError as e:
        raise credentials_exception from e

    user_db = db.query(UserDB).filter(UserDB.username == token_data.username).first()
    if user_db is None:
        raise credentials_exception

    return User.model_validate(user_db)


async def get_current_user_from_cookie(
    db: Annotated[Session, Depends(get_db)],
    session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Get the current user from the session cookie.

    Args:
        session: Session cookie
        db: SQLAlchemy database session

    Returns:
        User object

    Raises:
        HTTPException: If cookie is invalid or user not found

    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(session, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from e

    user_db = db.query(UserDB).filter(UserDB.username == username).first()
    if user_db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return User.model_validate(user_db)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Authenticate user and return an access token.

    Args:
        response: FastAPI response object for setting cookies
        form_data: OAuth2 password request form
        db: SQLAlchemy database session

    Returns:
        Token object

    Raises:
        HTTPException: If authentication fails

    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email},
        expires_delta=access_token_expires,
    )

    # Set cookie for authentication
    cookie_expires = int(access_token_expires.total_seconds())
    response.set_cookie(
        key="session",
        value=access_token,
        httponly=True,
        max_age=cookie_expires,
        expires=cookie_expires,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/login")
async def login(
    response: Response,
    login_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Login user with email and password.

    Args:
        response: FastAPI response object for setting cookies
        login_data: Login data containing email and password
        db: SQLAlchemy database session

    Returns:
        Message indicating successful login

    Raises:
        HTTPException: If authentication fails

    """
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email},
        expires_delta=access_token_expires,
    )

    # Set cookie for authentication
    cookie_expires = int(access_token_expires.total_seconds())
    response.set_cookie(
        key="session",
        value=access_token,
        httponly=True,
        max_age=cookie_expires,
        expires=cookie_expires,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return {"message": "Login successful"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Logout user by clearing the session cookie.

    Args:
        response: FastAPI response object for clearing cookies

    Returns:
        Message indicating successful logout

    """
    response.delete_cookie(key="session")
    return {"message": "Logout successful"}


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
) -> User:
    """Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    """
    return current_user
