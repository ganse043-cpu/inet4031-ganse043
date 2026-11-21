import csv
import io
import random
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
SEED = 4031
START = datetime(2026, 7, 27, tzinfo=timezone.utc)
SNAPSHOT = START + timedelta(weeks=16)

CATEGORIES = {
    "scanners and handhelds": ("Handheld scanner will not pair", 6),
    "dispatch app": ("Dispatch job fails to update", 12),
    "printers and labels": ("Shipping label prints incorrectly", 4),
    "logins and access": ("Dispatcher cannot sign in", 3),
    "network": ("Warehouse connection drops", 18),
}
FIELDS = ("ticket_id", "title", "category", "status", "created_at", "resolved_at")
COLUMNS = ", ".join(FIELDS)
PSQL = [
    "kubectl", "exec", "-i", "deploy/db", "--", "sh", "-c",
    'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"',
    "psql",
]


def generate_csv():
    rng = random.Random(SEED)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(FIELDS)
    ticket_id = 0

    for week in range(16):
        # Weekly counts rise from 600 to 900 and total 12,000.
        for _ in range(600 + 20 * week):
            ticket_id += 1
            day = rng.choices(range(7), weights=[5, 5, 5, 5, 5, 1, 1])[0]
            hour = rng.choices(
                range(24), weights=[5 if 8 <= h < 17 else 1 for h in range(24)]
            )[0]
            created_at = START + timedelta(
                weeks=week, days=day, hours=hour, minutes=rng.randrange(60)
            )
            category = rng.choice(tuple(CATEGORIES))
            title, median_hours = CATEGORIES[category]
            duration = timedelta(minutes=max(1, round(
                60 * median_hours * rng.lognormvariate(0, 0.9)
            )))
            resolved_at = created_at + duration
            if resolved_at <= SNAPSHOT:
                status = "closed"
                resolved_value = resolved_at.isoformat()
            else:
                status = rng.choice(("open", "in_progress"))
                resolved_value = ""
            writer.writerow((
                ticket_id, title, category, status,
                created_at.isoformat(), resolved_value,
            ))

    return stream.getvalue()


def load_and_export(generated_csv):
    # A failed import rolls back the reload, including the truncate.
    load_sql = rf"""
BEGIN;
CREATE TABLE IF NOT EXISTS public.capstone_tickets (
    ticket_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    CHECK ((status = 'closed') = (resolved_at IS NOT NULL)),
    CHECK (resolved_at > created_at)
);
TRUNCATE public.capstone_tickets;
\copy public.capstone_tickets ({COLUMNS}) FROM STDIN WITH (FORMAT csv, HEADER true)
{generated_csv}\.
COMMIT;
"""
    subprocess.run(PSQL, input=load_sql, text=True, check=True)

    export_sql = (
        f"COPY (SELECT {COLUMNS} FROM public.capstone_tickets ORDER BY ticket_id) "
        "TO STDOUT WITH (FORMAT csv, HEADER true)"
    )
    return subprocess.run(
        PSQL + ["-c", export_sql], stdout=subprocess.PIPE, text=True, check=True
    ).stdout


def write_quality(exported_csv):
    rows = list(csv.DictReader(io.StringIO(exported_csv)))
    created = [datetime.fromisoformat(row["created_at"]) for row in rows]
    span = (max(created) - min(created)).total_seconds() / 86400 if created else 0
    closed = [row for row in rows if row["status"] == "closed"]
    invalid_resolution = 0

    for row, created_at in zip(rows, created):
        resolved = row["resolved_at"]
        if not resolved:
            continue
        resolved_at = datetime.fromisoformat(resolved)
        if row["status"] != "closed" or not created_at < resolved_at <= SNAPSHOT:
            invalid_resolution += 1

    checks = [
        ("row_count", len(rows), len(rows) == 12_000),
        ("creation_span_days", round(span, 3), span >= 90),
        ("invalid_categories", sum(row["category"] not in CATEGORIES for row in rows), None),
        ("closed_missing_resolution", sum(not row["resolved_at"] for row in closed), None),
        ("invalid_resolution_timestamps", invalid_resolution, None),
        ("duplicate_ticket_ids", len(rows) - len({row["ticket_id"] for row in rows}), None),
    ]
    with (OUTPUT / "data_quality.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("check", "measured_value", "result"))
        writer.writerow(("earliest_created_at", min(created).isoformat() if created else "", ""))
        writer.writerow(("latest_created_at", max(created).isoformat() if created else "", ""))
        writer.writerow(("closed_ticket_count", len(closed), ""))
        for name, value, passed in checks:
            if passed is None:
                passed = value == 0
            writer.writerow((name, value, "pass" if passed else "fail"))

    return all(passed if passed is not None else value == 0 for _, value, passed in checks)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    exported_csv = load_and_export(generate_csv())
    (OUTPUT / "capstone_tickets.csv").write_text(exported_csv)
    if not write_quality(exported_csv):
        raise SystemExit("QA failed. See output/data_quality.csv.")
    print(f"QA passed. Results saved to {OUTPUT / 'data_quality.csv'}")


if __name__ == "__main__":
    main()