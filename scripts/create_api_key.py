#!/usr/bin/env python3
"""
Script to create a new API key for the Health Insurance API.

Usage:
    python scripts/create_api_key.py --name "My API Key" --description "Description here"
    python scripts/create_api_key.py --name "My API Key"  # Description is optional
"""

import asyncio
import argparse
import secrets
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, init_db
from app.models.api_key import ApiKey
from app.core.api_key import hash_api_key


async def create_api_key(name: str, description: str = None) -> tuple[str, ApiKey]:
    """
    Create a new API key.
    
    Args:
        name: Name for the API key
        description: Optional description
        
    Returns:
        Tuple of (plain_api_key, ApiKey model)
    """
    # Generate secure random API key (32 bytes = 256 bits)
    # Using SHA256 for hashing (no length limit like bcrypt)
    # 32 bytes (256 bits) is cryptographically secure
    plain_api_key = secrets.token_urlsafe(32)
    
    # Hash the API key
    key_hash = hash_api_key(plain_api_key)
    
    # Create API key record
    async with AsyncSessionLocal() as session:
        api_key = ApiKey(
            name=name,
            description=description,
            key_hash=key_hash,
            is_active=True
        )
        
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        
        return plain_api_key, api_key


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create a new API key for Health Insurance API"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name for the API key (required)"
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Description for the API key (optional)"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    await init_db()
    
    # Create API key
    try:
        plain_key, api_key = await create_api_key(
            name=args.name,
            description=args.description
        )
        
        print("\n" + "="*70)
        print("API KEY CREATED SUCCESSFULLY")
        print("="*70)
        print(f"ID: {api_key.id}")
        print(f"Name: {api_key.name}")
        if api_key.description:
            print(f"Description: {api_key.description}")
        print(f"Status: {'Active' if api_key.is_active else 'Inactive'}")
        print(f"Created: {api_key.created_at}")
        print("\n" + "-"*70)
        print("IMPORTANT: Save this API key now. It will NOT be shown again!")
        print("-"*70)
        print(f"\nAPI Key: {plain_key}\n")
        print("="*70)
        print("\nUse this key in the X-API-Key header for authenticated requests.")
        print("Example: X-API-Key: " + plain_key[:50] + "...")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"Error creating API key: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

