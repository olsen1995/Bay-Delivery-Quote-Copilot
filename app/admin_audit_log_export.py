import csv
import io
from fastapi import Request, Response, HTTPException
from app.audit_log import AUDIT_TABLE_NAME
from app.storage import _connect

# CSV export utility for admin audit log

def export_admin_audit_log_csv(request: Request) -> Response:
    # Auth check: reuse main.py _require_admin
    from app.main import _require_admin
    _require_admin(request)

    conn = _connect()
    try:
        cursor = conn.execute(f"SELECT * FROM {AUDIT_TABLE_NAME} ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")
    output.close()

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=admin_audit_log.csv"
        },
    )
