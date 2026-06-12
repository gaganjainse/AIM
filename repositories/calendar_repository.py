from __future__ import annotations

from repositories.db_utils import fetch_all


def attendance_events():
    return fetch_all(
        """
        SELECT date,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent,
               SUM(CASE WHEN status='Leave' THEN 1 ELSE 0 END) AS leave_count,
               COUNT(status) AS total
        FROM attendance
        GROUP BY date
        """
    )
