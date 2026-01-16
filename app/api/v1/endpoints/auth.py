from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_operator
from app.schemas.auth import GoogleAuthRequest, GoogleAuthResponse, CurrentUserResponse
from app.services.operator_service import OperatorService
from app.services.audit_service import AuditService
from app.core.security import create_access_token, verify_google_token
from app.models.audit_log import ActionType, UserType
from app.models.operator import Operator
from datetime import timedelta
from app.config import settings

router = APIRouter()


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(
    request: GoogleAuthRequest,
    background_tasks: BackgroundTasks,
    request_obj: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate with Google SSO and return JWT token.
    """
    # Verify Google token
    user_info = await verify_google_token(request.token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found in Google token"
        )
    
    # Get or validate operator
    operator = await OperatorService.get_operator_by_email(db, email)
    if not operator or not operator.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator not authorized"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(operator.id), "email": email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Log login
    await AuditService.log_action_background(
        background_tasks=background_tasks,
        db=db,
        action_type=ActionType.OPERATOR_LOGIN,
        user_type=UserType.OPERATOR,
        user_id=operator.id,
        ip_address=request_obj.client.host,
        user_agent=request_obj.headers.get("user-agent")
    )
    
    return GoogleAuthResponse(
        access_token=access_token,
        token_type="bearer",
        operator_id=operator.id,
        email=operator.google_email,
        name=operator.name
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    current_operator: Operator = Depends(get_current_operator)
):
    """
    Get current user information from JWT token.
    """
    return CurrentUserResponse(
        id=current_operator.id,
        email=current_operator.google_email,
        name=current_operator.name,
        is_active=current_operator.is_active
    )


@router.post("/test-superadmin", response_model=GoogleAuthResponse)
async def test_superadmin_login(
    background_tasks: BackgroundTasks,
    request_obj: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    TEST ONLY - Create/Login as superadmin bypassing Google SSO.
    Only works when ENVIRONMENT=development or ENVIRONMENT=test.
    Superadmin has full ACL management and bypasses all permission checks.
    """
    if settings.ENVIRONMENT not in ["development", "test"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    
    # Find or create superadmin operator
    superadmin_email = "superadmin@test.local"
    operator = await OperatorService.get_operator_by_email(db, superadmin_email)
    
    if not operator:
        # Create superadmin operator
        operator = await OperatorService.create_operator(
            db=db,
            google_email=superadmin_email,
            name="Test Superadmin"
        )
        # Mark as superadmin
        operator.is_superadmin = True
        await db.commit()
        await db.refresh(operator)
    else:
        # Ensure it's marked as superadmin
        if not operator.is_superadmin:
            operator.is_superadmin = True
            await db.commit()
            await db.refresh(operator)
    
    # Ensure operator is active
    if not operator.is_active:
        operator.is_active = True
        await db.commit()
        await db.refresh(operator)
    
    # Create JWT token with superadmin flag
    access_token = create_access_token(
        data={
            "sub": str(operator.id),
            "email": operator.google_email,
            "is_superadmin": True
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Log login
    await AuditService.log_action_background(
        background_tasks=background_tasks,
        db=db,
        action_type=ActionType.OPERATOR_LOGIN,
        user_type=UserType.OPERATOR,
        user_id=operator.id,
        ip_address=request_obj.client.host,
        user_agent=request_obj.headers.get("user-agent"),
        request_data={"test_superadmin": True}
    )
    
    return GoogleAuthResponse(
        access_token=access_token,
        token_type="bearer",
        operator_id=operator.id,
        email=operator.google_email,
        name=operator.name
    )

