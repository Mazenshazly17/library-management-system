import json
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.cache import check_redis_connection, flush_cache, get_cache_stats, get_redis
from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger
from app.core.security import require_admin
from app.models.book import Book
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.user import User

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/stats", summary="System statistics", dependencies=[Depends(require_admin)])
def get_system_stats(db: Session = Depends(get_db)):
    total_books = db.query(func.count(Book.id)).filter(Book.is_active == True).scalar()
    available_books = db.query(func.count(Book.id)).filter(
        Book.is_active == True,
        Book.available_copies > 0,
    ).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    active_borrows = db.query(func.count(BorrowRecord.id)).filter(
        BorrowRecord.status == BorrowStatus.active,
    ).scalar()
    pending_borrows = db.query(func.count(BorrowRecord.id)).filter(
        BorrowRecord.status == BorrowStatus.pending,
    ).scalar()
    overdue_borrows = db.query(func.count(BorrowRecord.id)).filter(
        BorrowRecord.status == BorrowStatus.overdue,
    ).scalar()
    returned_borrows = db.query(func.count(BorrowRecord.id)).filter(
        BorrowRecord.status == BorrowStatus.returned,
    ).scalar()
    total_borrows = db.query(func.count(BorrowRecord.id)).scalar()

    db_latency_ms = None
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception as exc:
        logger.error(f"Monitoring DB probe failed: {exc}")

    redis_latency_ms = None
    redis_available = check_redis_connection()
    if redis_available:
        try:
            client = get_redis()
            start = time.perf_counter()
            client.ping()
            redis_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        except Exception as exc:
            logger.warning(f"Monitoring Redis probe failed: {exc}")
            redis_available = False

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "library": {
            "total_books": total_books,
            "available_books": available_books,
            "total_users": total_users,
            "active_borrows": active_borrows,
            "pending_borrows": pending_borrows,
            "overdue_borrows": overdue_borrows,
            "returned_borrows": returned_borrows,
            "total_borrow_records": total_borrows,
        },
        "cache": get_cache_stats(),
        "infrastructure": {
            "database_latency_ms": db_latency_ms,
            "redis_latency_ms": redis_latency_ms,
            "redis_available": redis_available,
        },
    }


@router.get("/cache/stats", summary="Redis cache statistics", dependencies=[Depends(require_admin)])
def get_cache_statistics():
    return get_cache_stats()


@router.post("/cache/flush", summary="Flush Redis cache", dependencies=[Depends(require_admin)])
def flush_all_cache(pattern: str = Query(default="*", description="Redis key pattern")):
    removed = flush_cache(pattern)
    logger.warning(f"Cache flush requested: pattern={pattern} removed={removed}")
    return {"message": f"Cache flushed for pattern '{pattern}'", "keys_removed": removed}


@router.get("/logs/recent", summary="Recent log entries", dependencies=[Depends(require_admin)])
def get_recent_logs(
    lines: int = Query(default=50, ge=1, le=500),
    level: str = Query(default="INFO"),
):
    log_file = settings.LOG_FILE
    if not os.path.exists(log_file):
        return {"entries": [], "message": "Log file not found yet"}

    level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_order.get(level.upper(), 1)
    entries = []

    try:
        with open(log_file, "r", encoding="utf-8") as handle:
            raw_lines = handle.readlines()

        for raw_line in reversed(raw_lines):
            if len(entries) >= lines:
                break
            try:
                payload = json.loads(raw_line.strip())
                record = payload.get("record", {})
                entry_level = record.get("level", {}).get("name", "INFO")
                if level_order.get(entry_level, 0) >= min_level:
                    entries.append(
                        {
                            "time": record.get("time", {}).get("repr", ""),
                            "level": entry_level,
                            "module": record.get("name", ""),
                            "message": record.get("message", ""),
                        }
                    )
            except Exception:
                entries.append({"raw": raw_line.strip()})

        return {"returned": len(entries), "entries": entries}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read log file: {exc}")


@router.get("/health/detailed", summary="Detailed dependency health")
def detailed_health(db: Session = Depends(get_db)):
    dependencies = {}

    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        dependencies["database"] = {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception as exc:
        dependencies["database"] = {"status": "error", "detail": str(exc)}

    try:
        client = get_redis()
        if client:
            start = time.perf_counter()
            client.ping()
            dependencies["redis"] = {
                "status": "ok",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        else:
            dependencies["redis"] = {"status": "unavailable"}
    except Exception as exc:
        dependencies["redis"] = {"status": "error", "detail": str(exc)}

    overall = "healthy" if all(
        item.get("status") == "ok" for item in dependencies.values()
    ) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "dependencies": dependencies,
    }


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Library Monitoring</title>
  <style>
    body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#111827;color:#e5e7eb}
    header{display:flex;justify-content:space-between;align-items:center;padding:20px 28px;background:#0f172a;border-bottom:1px solid #334155}
    h1{font-size:22px;margin:0}.badge{padding:6px 10px;border-radius:999px;background:#064e3b;color:#86efac;font-size:13px}
    main{max-width:1120px;margin:28px auto;padding:0 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
    .card{background:#1f2937;border:1px solid #374151;border-radius:8px;padding:18px}.label{color:#9ca3af;font-size:12px;text-transform:uppercase}
    .value{font-size:30px;font-weight:800;margin-top:8px}.wide{margin-top:18px}.error{display:none;background:#7f1d1d;color:#fecaca;padding:12px;border-radius:8px;margin-bottom:14px}
    a{color:#93c5fd}code{background:#0f172a;padding:2px 6px;border-radius:5px}
  </style>
</head>
<body>
  <header><h1>Library Monitoring</h1><span id="state" class="badge">Loading</span></header>
  <main>
    <div id="error" class="error"></div>
    <section class="grid">
      <div class="card"><div class="label">Total Books</div><div id="books" class="value">--</div></div>
      <div class="card"><div class="label">Available Books</div><div id="available" class="value">--</div></div>
      <div class="card"><div class="label">Users</div><div id="users" class="value">--</div></div>
      <div class="card"><div class="label">Active Borrows</div><div id="active" class="value">--</div></div>
      <div class="card"><div class="label">Overdue</div><div id="overdue" class="value">--</div></div>
      <div class="card"><div class="label">Cache Hit Rate</div><div id="cache" class="value">--</div></div>
    </section>
    <section class="card wide">
      <div class="label">Infrastructure</div>
      <p>Database: <code id="db">--</code></p>
      <p>Redis: <code id="redis">--</code></p>
      <p>Prometheus metrics: <a href="/metrics">/metrics</a></p>
      <p>Swagger: <a href="/docs">/docs</a></p>
    </section>
  </main>
  <script>
    async function load(){
      const token=localStorage.getItem('library_access_token');
      const headers=token?{Authorization:'Bearer '+token}:{};
      try{
        const res=await fetch('/api/v1/monitoring/stats',{headers});
        if(!res.ok) throw new Error('Admin token required for full dashboard. Login in the frontend first.');
        const data=await res.json(), lib=data.library, cache=data.cache, infra=data.infrastructure;
        books.textContent=lib.total_books; available.textContent=lib.available_books; users.textContent=lib.total_users;
        active.textContent=lib.active_borrows; overdue.textContent=lib.overdue_borrows;
        window.cache.textContent=cache.available?cache.hit_rate_percent+'%':'N/A';
        db.textContent=infra.database_latency_ms!==null?infra.database_latency_ms+'ms':'error';
        redis.textContent=infra.redis_available?(infra.redis_latency_ms+'ms'):'unavailable';
        state.textContent='Healthy'; error.style.display='none';
      }catch(e){
        state.textContent='Limited';
        error.style.display='block';
        error.textContent=e.message;
        const health=await fetch('/api/v1/monitoring/health/detailed').then(r=>r.json());
        db.textContent=health.dependencies.database.status;
        redis.textContent=health.dependencies.redis.status;
      }
    }
    load(); setInterval(load,10000);
  </script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse, summary="Built-in monitoring dashboard")
def monitoring_dashboard():
    return HTMLResponse(DASHBOARD_HTML)
