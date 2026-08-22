"""Tests for borrowing, returning, history, and all business rule enforcement."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_token, auth_headers
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.book import Book
from app.core.security import hash_password
from app.models.user import User, UserRole


def request_borrow(client: TestClient, token: str, book_id: int, duration_days: int = 7):
    return client.post(
        "/api/v1/borrows",
        headers=auth_headers(token),
        json={"book_id": book_id, "duration_days": duration_days},
    )


def approve_borrow(client: TestClient, admin_token: str, record_id: int):
    return client.post(f"/api/v1/borrows/{record_id}/approve", headers=auth_headers(admin_token))


def request_and_approve(
    client: TestClient,
    borrower_token: str,
    admin_token: str,
    book_id: int,
    duration_days: int = 7,
):
    borrow_resp = request_borrow(client, borrower_token, book_id, duration_days)
    assert borrow_resp.status_code == 201, borrow_resp.text
    record_id = borrow_resp.json()["id"]
    approve_resp = approve_borrow(client, admin_token, record_id)
    assert approve_resp.status_code == 200, approve_resp.text
    return approve_resp


class TestBorrowBook:
    def test_borrow_available_book(self, client: TestClient, member_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        resp = request_borrow(client, token, sample_book.id, duration_days=10)
        assert resp.status_code == 201
        data = resp.json()
        assert data["book_id"] == sample_book.id
        assert data["user_id"] == member_user.id
        assert data["status"] == "pending"
        assert data["requested_duration_days"] == 10
        assert data["due_date"] is not None

    def test_borrow_unavailable_book(self, client: TestClient, member_user, unavailable_book):
        token = get_token(client, "member@library.com", "Member1234")
        resp = request_borrow(client, token, unavailable_book.id)
        assert resp.status_code == 400
        assert "unavailable" in resp.json()["detail"].lower()

    def test_borrow_nonexistent_book(self, client: TestClient, member_user):
        token = get_token(client, "member@library.com", "Member1234")
        resp = request_borrow(client, token, 99999)
        assert resp.status_code == 404

    def test_borrow_request_does_not_decrement_available_copies(self, client: TestClient, member_user, sample_book, db):
        token = get_token(client, "member@library.com", "Member1234")
        initial_copies = sample_book.available_copies
        request_borrow(client, token, sample_book.id)
        db.refresh(sample_book)
        assert sample_book.available_copies == initial_copies

    def test_admin_approval_decrements_available_copies(self, client: TestClient, member_user, admin_user, sample_book, db):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        initial_copies = sample_book.available_copies

        approve_resp = request_and_approve(client, member_token, admin_token, sample_book.id, duration_days=3)

        assert approve_resp.json()["status"] == "active"
        assert approve_resp.json()["requested_duration_days"] == 3
        db.refresh(sample_book)
        assert sample_book.available_copies == initial_copies - 1

    def test_admin_can_reject_pending_request(self, client: TestClient, member_user, admin_user, sample_book, db):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        initial_copies = sample_book.available_copies

        borrow_resp = request_borrow(client, member_token, sample_book.id)
        record_id = borrow_resp.json()["id"]
        reject_resp = client.post(
            f"/api/v1/borrows/{record_id}/reject",
            headers=auth_headers(admin_token),
            json={"notes": "Not available for this member"},
        )

        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"
        db.refresh(sample_book)
        assert sample_book.available_copies == initial_copies

    def test_member_cannot_approve_request(self, client: TestClient, member_user, sample_book):
        member_token = get_token(client, "member@library.com", "Member1234")
        borrow_resp = request_borrow(client, member_token, sample_book.id)
        record_id = borrow_resp.json()["id"]

        resp = approve_borrow(client, member_token, record_id)
        assert resp.status_code == 403

    def test_prevent_duplicate_active_borrow(self, client: TestClient, member_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        # First request
        r1 = request_borrow(client, token, sample_book.id)
        assert r1.status_code == 201
        # Second open request of same book
        r2 = request_borrow(client, token, sample_book.id)
        assert r2.status_code == 409

    def test_borrow_limit_enforcement(self, client: TestClient, member_user, db):
        """Cannot create more than MAX_BORROWED_BOOKS open requests/borrows."""
        from app.core.config import settings
        token = get_token(client, "member@library.com", "Member1234")

        # Create enough books
        for i in range(settings.MAX_BORROWED_BOOKS + 1):
            book = Book(title=f"Limit Book {i}", author="Author", total_copies=2, available_copies=2)
            db.add(book)
        db.commit()
        db.expire_all()

        books = db.query(Book).filter(Book.title.like("Limit Book%")).all()

        # Request up to the limit
        for i in range(settings.MAX_BORROWED_BOOKS):
            r = request_borrow(client, token, books[i].id)
            assert r.status_code == 201, f"Borrow request {i+1} failed: {r.text}"

        # One more should fail
        r = request_borrow(client, token, books[settings.MAX_BORROWED_BOOKS].id)
        assert r.status_code == 400
        assert "limit" in r.json()["detail"].lower()


class TestReturnBook:
    def test_return_borrowed_book(self, client: TestClient, member_user, admin_user, sample_book, db):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        approve_resp = request_and_approve(client, member_token, admin_token, sample_book.id)
        record_id = approve_resp.json()["id"]

        # Return
        resp = client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(member_token), json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

    def test_return_restores_available_copies(self, client: TestClient, member_user, admin_user, sample_book, db):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        initial = sample_book.available_copies

        approve_resp = request_and_approve(client, member_token, admin_token, sample_book.id)
        record_id = approve_resp.json()["id"]
        client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(member_token), json={})

        db.refresh(sample_book)
        assert sample_book.available_copies == initial

    def test_cannot_return_already_returned(self, client: TestClient, member_user, admin_user, sample_book):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        approve_resp = request_and_approve(client, member_token, admin_token, sample_book.id)
        record_id = approve_resp.json()["id"]
        client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(member_token), json={})
        # Return again
        resp = client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(member_token), json={})
        assert resp.status_code == 409

    def test_member_cannot_return_others_book(self, client: TestClient, member_user, admin_user, sample_book, db):
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        approve_resp = request_and_approve(client, admin_token, admin_token, sample_book.id)
        record_id = approve_resp.json()["id"]

        # Member tries to return admin's book
        member_token = get_token(client, "member@library.com", "Member1234")
        resp = client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(member_token), json={})
        assert resp.status_code == 403

    def test_admin_can_return_any_book(self, client: TestClient, member_user, admin_user, sample_book):
        member_token = get_token(client, "member@library.com", "Member1234")
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        approve_resp = request_and_approve(client, member_token, admin_token, sample_book.id)
        record_id = approve_resp.json()["id"]

        # Admin returns
        resp = client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(admin_token), json={})
        assert resp.status_code == 200

    def test_cannot_return_pending_request(self, client: TestClient, member_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        borrow_resp = request_borrow(client, token, sample_book.id)
        record_id = borrow_resp.json()["id"]

        resp = client.post(f"/api/v1/borrows/{record_id}/return", headers=auth_headers(token), json={})
        assert resp.status_code == 409


class TestBorrowHistory:
    def test_member_sees_own_history(self, client: TestClient, member_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        request_borrow(client, token, sample_book.id)
        resp = client.get("/api/v1/borrows", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for record in data["items"]:
            assert record["user_id"] == member_user.id

    def test_admin_sees_all_records(self, client: TestClient, admin_user, member_user, sample_book):
        # Member borrows
        member_token = get_token(client, "member@library.com", "Member1234")
        request_borrow(client, member_token, sample_book.id)

        # Admin lists all
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        resp = client.get("/api/v1/borrows", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_status(self, client: TestClient, member_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        request_borrow(client, token, sample_book.id)
        resp = client.get("/api/v1/borrows?status=pending", headers=auth_headers(token))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "pending"

    def test_user_history_endpoint(self, client: TestClient, member_user, admin_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")
        request_borrow(client, token, sample_book.id)

        admin_token = get_token(client, "admin@library.com", "Admin1234")
        resp = client.get(f"/api/v1/borrows/users/{member_user.id}/history", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_mark_overdue_admin_only(self, client: TestClient, admin_user, member_user):
        admin_token = get_token(client, "admin@library.com", "Admin1234")
        resp = client.post("/api/v1/borrows/admin/mark-overdue", headers=auth_headers(admin_token))
        assert resp.status_code == 200

        member_token = get_token(client, "member@library.com", "Member1234")
        resp2 = client.post("/api/v1/borrows/admin/mark-overdue", headers=auth_headers(member_token))
        assert resp2.status_code == 403


class TestRequiredBorrowAliases:
    def test_borrow_and_return_required_paths(self, client: TestClient, member_user, admin_user, sample_book):
        token = get_token(client, "member@library.com", "Member1234")

        borrow_resp = client.post(
            f"/api/v1/borrow/{sample_book.id}",
            headers=auth_headers(token),
            json={"duration_days": 5},
        )
        assert borrow_resp.status_code == 201
        record_id = borrow_resp.json()["id"]
        assert borrow_resp.json()["status"] == "pending"
        assert borrow_resp.json()["requested_duration_days"] == 5

        my_records = client.get("/api/v1/borrow-records/me", headers=auth_headers(token))
        assert my_records.status_code == 200
        assert my_records.json()["total"] >= 1

        get_record = client.get(f"/api/v1/borrow-records/{record_id}", headers=auth_headers(token))
        assert get_record.status_code == 200
        assert get_record.json()["id"] == record_id

        admin_token = get_token(client, "admin@library.com", "Admin1234")
        approve_resp = approve_borrow(client, admin_token, record_id)
        assert approve_resp.status_code == 200

        return_resp = client.post(f"/api/v1/return/{record_id}", headers=auth_headers(token), json={})
        assert return_resp.status_code == 200
        assert return_resp.json()["status"] == "returned"
