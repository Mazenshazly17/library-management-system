from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.borrow_record import BorrowStatus
from app.schemas.borrow_record import (
    BorrowByPathRequest, BorrowDecisionRequest, BorrowRequest, ReturnRequest,
    BorrowRecordResponse, BorrowFilter,
)
from app.schemas.common import PaginatedResponse, PaginationParams, get_pagination_params, MessageResponse
from app.services.borrow_service import BorrowService
from app.core.logger import logger

router = APIRouter(prefix="/borrows", tags=["Borrow Records"])
compat_router = APIRouter(tags=["Borrow Records"])


@router.post(
    "",
    response_model=BorrowRecordResponse,
    status_code=201,
    summary="Request to borrow a book",
    description=(
        "Members can request an available book with a borrowing duration. "
        "The book is assigned only after admin approval."
    ),
)
def borrow_book(
    data: BorrowRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return BorrowService.borrow_book(db, current_user, data)


@router.post(
    "/{record_id}/approve",
    response_model=BorrowRecordResponse,
    summary="Approve a pending borrow request (Admin only)",
)
def approve_borrow_request(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return BorrowService.approve_request(db, record_id)


@router.post(
    "/{record_id}/reject",
    response_model=BorrowRecordResponse,
    summary="Reject a pending borrow request (Admin only)",
)
def reject_borrow_request(
    record_id: int,
    data: BorrowDecisionRequest = BorrowDecisionRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return BorrowService.reject_request(db, record_id, data)


@router.post(
    "/{record_id}/return",
    response_model=BorrowRecordResponse,
    summary="Return a borrowed book",
    description="Members return their own books. Admins can return any book.",
)
def return_book(
    record_id: int,
    data: ReturnRequest = ReturnRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return BorrowService.return_book(db, current_user, record_id, data)


@router.get(
    "",
    response_model=PaginatedResponse[BorrowRecordResponse],
    summary="List borrow records",
    description=(
        "Admins see all records and can filter by user/book/status. "
        "Members only see their own history."
    ),
)
def list_borrow_records(
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: Optional[int] = Query(None, description="Filter by user ID (Admin only)"),
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    status: Optional[BorrowStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = BorrowFilter(user_id=user_id, book_id=book_id, status=status)
    records, total = BorrowService.list_records(db, pagination, filters, current_user)
    return PaginatedResponse.create(
        items=[BorrowRecordResponse.model_validate(r) for r in records],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{record_id}",
    response_model=BorrowRecordResponse,
    summary="Get borrow record by ID",
)
def get_borrow_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = BorrowService.get_by_id(db, record_id)
    # Members can only view their own records
    if current_user.role == "member" and record.user_id != current_user.id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return record


@router.get(
    "/users/{user_id}/history",
    response_model=PaginatedResponse[BorrowRecordResponse],
    summary="Get borrowing history for a specific user",
)
def get_user_history(
    user_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Members can only view their own history
    if current_user.role == "member" and current_user.id != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own borrowing history",
        )
    records, total = BorrowService.get_user_history(db, user_id, pagination)
    return PaginatedResponse.create(
        items=[BorrowRecordResponse.model_validate(r) for r in records],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/mark-overdue",
    response_model=MessageResponse,
    summary="Mark overdue records (Admin only)",
    description="Scans all active records and marks past-due ones as 'overdue'.",
    dependencies=[Depends(require_admin)],
)
def mark_overdue(db: Session = Depends(get_db)):
    count = BorrowService.mark_overdue(db)
    return {"message": f"Marked {count} record(s) as overdue"}


@compat_router.post(
    "/borrow/{book_id}",
    response_model=BorrowRecordResponse,
    status_code=201,
    summary="Borrow a book by book ID",
)
def borrow_book_by_path(
    book_id: int,
    data: BorrowByPathRequest = BorrowByPathRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return BorrowService.borrow_book(
        db,
        current_user,
        BorrowRequest(book_id=book_id, duration_days=data.duration_days, notes=data.notes),
    )


@compat_router.post(
    "/return/{borrow_record_id}",
    response_model=BorrowRecordResponse,
    summary="Return a borrowed book by record ID",
)
def return_book_by_path(
    borrow_record_id: int,
    data: ReturnRequest = ReturnRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return BorrowService.return_book(db, current_user, borrow_record_id, data)


@compat_router.get(
    "/borrow-records/me",
    response_model=PaginatedResponse[BorrowRecordResponse],
    summary="Get current user's borrow history",
)
def get_my_borrow_records(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[BorrowStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = BorrowFilter(user_id=current_user.id, status=status)
    records, total = BorrowService.list_records(db, pagination, filters, current_user)
    return PaginatedResponse.create(
        items=[BorrowRecordResponse.model_validate(r) for r in records],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@compat_router.get(
    "/borrow-records",
    response_model=PaginatedResponse[BorrowRecordResponse],
    summary="List borrow records",
)
def list_borrow_records_compat(
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: Optional[int] = Query(None, description="Filter by user ID (Admin only)"),
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    status: Optional[BorrowStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = BorrowFilter(user_id=user_id, book_id=book_id, status=status)
    records, total = BorrowService.list_records(db, pagination, filters, current_user)
    return PaginatedResponse.create(
        items=[BorrowRecordResponse.model_validate(r) for r in records],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@compat_router.get(
    "/borrow-records/{record_id}",
    response_model=BorrowRecordResponse,
    summary="Get borrow record by ID",
)
def get_borrow_record_compat(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_borrow_record(record_id, db, current_user)
