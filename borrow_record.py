from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.borrow_record import BorrowStatus
from app.schemas.book import BookSummary
from app.schemas.user import UserPublicResponse


class BorrowRequest(BaseModel):
    book_id: int = Field(..., description="ID of the book to borrow")
    duration_days: int = Field(
        ...,
        ge=1,
        le=settings.MAX_BORROW_DAYS,
        description="Requested borrowing duration in days",
    )
    notes: Optional[str] = Field(None, max_length=500)


class BorrowByPathRequest(BaseModel):
    duration_days: int = Field(
        default=settings.MAX_BORROW_DAYS,
        ge=1,
        le=settings.MAX_BORROW_DAYS,
        description="Requested borrowing duration in days",
    )
    notes: Optional[str] = Field(None, max_length=500)


class BorrowDecisionRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)


class ReturnRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)


class BorrowRecordResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    status: BorrowStatus
    requested_duration_days: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    # Nested objects
    book: Optional[BookSummary] = None
    user: Optional[UserPublicResponse] = None

    model_config = {"from_attributes": True}


class BorrowRecordSummary(BaseModel):
    """Lightweight borrow info."""
    id: int
    user_id: int
    book_id: int
    status: BorrowStatus
    requested_duration_days: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: Optional[datetime]

    model_config = {"from_attributes": True}


class BorrowFilter(BaseModel):
    """Query filters for borrow records."""
    user_id: Optional[int] = None
    book_id: Optional[int] = None
    status: Optional[BorrowStatus] = None
