from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

DB_PATH = Path(__file__).resolve().parent / "jobs.db"
STATUS_OPTIONS = ["applied", "interview", "offer", "rejected"]


def normalize_optional_date(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned).isoformat()
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc


class JobCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    date_applied: str = Field(..., min_length=1, max_length=20)
    status: str = Field(default="applied")
    notes: str = Field(default="")
    follow_up_date: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in STATUS_OPTIONS:
            allowed = ", ".join(STATUS_OPTIONS)
            raise ValueError(f"Status must be one of: {allowed}")
        return normalized

    @field_validator("follow_up_date")
    @classmethod
    def validate_follow_up_date(cls, value: str | None) -> str | None:
        return normalize_optional_date(value)


class JobUpdate(JobCreate):
    pass


class JobRecord(JobCreate):
    id: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Tracker API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_follow_up_column(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(jobs)").fetchall()
    existing = {row[1] for row in cols}
    if "follow_up_date" not in existing:
        conn.execute("ALTER TABLE jobs ADD COLUMN follow_up_date TEXT")


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT DEFAULT '',
                follow_up_date TEXT
            )
            """
        )
        ensure_follow_up_column(conn)

        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        if total == 0:
            sample_jobs = [
                (
                    "Acme",
                    "Product Designer",
                    "2025-10-27",
                    "interview",
                    "Phone screen scheduled with design lead.",
                    "2025-11-03",
                ),
                (
                    "Northstar Labs",
                    "Frontend Engineer",
                    "2025-10-28",
                    "applied",
                    "Applied through the company careers page.",
                    "2025-11-02",
                ),
            ]
            conn.executemany(
                """
                INSERT INTO jobs (company, position, date_applied, status, notes, follow_up_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                sample_jobs,
            )
        conn.commit()


def row_to_job(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "company": row["company"],
        "position": row["position"],
        "date_applied": row["date_applied"],
        "status": row["status"],
        "notes": row["notes"],
        "follow_up_date": row["follow_up_date"],
    }


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/jobs")
def list_jobs(
    status: str | None = None,
    search: str | None = None,
    sort: str = "date_applied",
    direction: str = "desc",
) -> list[dict]:
    clauses: list[str] = []
    params: list[str] = []

    if status and status != "all":
        clauses.append("LOWER(status) = LOWER(?)")
        params.append(status)

    if search:
        search_text = f"%{search.lower()}%"
        clauses.append("(LOWER(company) LIKE ? OR LOWER(position) LIKE ? OR LOWER(notes) LIKE ?)")
        params.extend([search_text, search_text, search_text])

    query = "SELECT * FROM jobs"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    allowed_sort = {"company", "position", "date_applied", "status"}
    sort_value = sort if sort in allowed_sort else "date_applied"
    order = "ASC" if direction.lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_value} {order}, id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [row_to_job(row) for row in rows]


@app.get("/api/activity")
def get_activity() -> dict[str, list[str] | list[int]]:
    today = date.today()
    labels: list[str] = []
    values: list[int] = []

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime("%a"))
        values.append(0)

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date_applied, COUNT(*) AS count FROM jobs GROUP BY date_applied"
        ).fetchall()

    for row in rows:
        row_date = parse_date(row["date_applied"])
        if row_date is None:
            continue
        delta = (today - row_date).days
        if delta < 0:
            continue
        if delta <= 6:
            index = 6 - delta
            values[index] += int(row["count"])

    return {"labels": labels, "values": values}


@app.get("/api/reminders")
def get_reminders() -> dict[str, list[dict]]:
    today = date.today()
    upcoming: list[dict] = []
    overdue: list[dict] = []

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE follow_up_date IS NOT NULL ORDER BY follow_up_date ASC"
        ).fetchall()

    for row in rows:
        due = parse_date(row["follow_up_date"])
        if due is None:
            continue
        delta = (due - today).days
        item = {
            "id": row["id"],
            "company": row["company"],
            "position": row["position"],
            "status": row["status"],
            "follow_up_date": row["follow_up_date"],
            "days_until": delta,
        }
        if delta < 0:
            overdue.append(item)
        elif delta <= 7:
            upcoming.append(item)

    return {"upcoming": upcoming, "overdue": overdue}


@app.get("/api/stats")
def get_stats() -> dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
        ).fetchall()

    counts = {status: 0 for status in STATUS_OPTIONS}
    for row in rows:
        value = row["status"].lower()
        if value in counts:
            counts[value] = int(row["count"])

    total = sum(counts.values())
    return {
        "total": total,
        "applied": counts["applied"],
        "interview": counts["interview"],
        "offer": counts["offer"],
        "rejected": counts["rejected"],
    }


@app.get("/api/jobs/export")
def export_jobs_csv() -> StreamingResponse:
    rows = list_jobs()
    stream = io.StringIO()
    fieldnames = ["id", "company", "position", "date_applied", "status", "notes", "follow_up_date"]
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "id": row.get("id", ""),
            "company": row.get("company", ""),
            "position": row.get("position", ""),
            "date_applied": row.get("date_applied", ""),
            "status": row.get("status", ""),
            "notes": row.get("notes", ""),
            "follow_up_date": row.get("follow_up_date", ""),
        })

    response = StreamingResponse(
        io.BytesIO(stream.getvalue().encode("utf-8")),
        media_type="text/csv",
    )
    response.headers["Content-Disposition"] = 'attachment; filename="job_tracker_export.csv"'
    return response


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobCreate) -> dict:
    cleaned = {
        "company": payload.company.strip(),
        "position": payload.position.strip(),
        "date_applied": payload.date_applied.strip(),
        "status": payload.status.strip().lower(),
        "notes": payload.notes.strip(),
        "follow_up_date": payload.follow_up_date,
    }

    if not cleaned["company"] or not cleaned["position"] or not cleaned["date_applied"]:
        raise HTTPException(status_code=400, detail="Company, position, and date_applied are required.")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO jobs (company, position, date_applied, status, notes, follow_up_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned["company"],
                cleaned["position"],
                cleaned["date_applied"],
                cleaned["status"],
                cleaned["notes"],
                cleaned["follow_up_date"],
            ),
        )
        job_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    return row_to_job(row)


@app.put("/api/jobs/{job_id}")
def update_job(job_id: int, payload: JobUpdate) -> dict:
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Job not found.")

        conn.execute(
            """
            UPDATE jobs
            SET company = ?, position = ?, date_applied = ?, status = ?, notes = ?, follow_up_date = ?
            WHERE id = ?
            """,
            (
                payload.company.strip(),
                payload.position.strip(),
                payload.date_applied.strip(),
                payload.status.strip().lower(),
                payload.notes.strip(),
                payload.follow_up_date,
                job_id,
            ),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    return row_to_job(row)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int) -> dict[str, str]:
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    return {"status": "deleted", "job_id": str(job_id)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
