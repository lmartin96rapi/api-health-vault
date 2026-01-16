from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from hashlib import sha256
from app.models.api_key import ApiKey
from app.database import get_db


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage using SHA256.
    Using SHA256 instead of bcrypt because:
    - API keys are already random (not user-chosen passwords)
    - SHA256 doesn't have length limitations like bcrypt (72 bytes)
    - Still secure for API key storage
    """
    return sha256(api_key.encode('utf-8')).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    computed_hash = sha256(plain_key.encode('utf-8')).hexdigest()
    return computed_hash == hashed_key


async def get_api_key_from_header(
    x_api_key: Optional[str],
    db: AsyncSession
) -> Optional[ApiKey]:
    """
    Extract and validate API key from header.
    
    Args:
        x_api_key: API key from X-API-Key header
        db: Database session
        
    Returns:
        ApiKey model if valid, None otherwise
    """
    if not x_api_key:
        return None
    
    if not db:
        return None
    
    # Query all active API keys
    result = await db.execute(
        select(ApiKey).where(ApiKey.is_active == True)
    )
    api_keys = result.scalars().all()
    
    # Check each API key hash
    for api_key in api_keys:
        if verify_api_key(x_api_key, api_key.key_hash):
            return api_key
    
    return None


async def validate_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> ApiKey:
    """
    Validate API key and raise exception if invalid.
    
    Args:
        x_api_key: API key from X-API-Key header
        db: Database session
        
    Returns:
        ApiKey model if valid
        
    Raises:
        HTTPException if API key is invalid or missing
    """
    api_key = await get_api_key_from_header(x_api_key, db)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key

