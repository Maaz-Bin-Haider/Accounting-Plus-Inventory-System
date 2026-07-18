"""Shared helper to turn database errors into user-friendly messages.

The stored procedures raise clear, curated messages with RAISE EXCEPTION
(SQLSTATE P0001). Those messages are written for end users and are safe to
display. Any other database error (connection problems, constraint
violations, programming errors) falls back to the generic message supplied
by the caller so internal details are never leaked to the browser.
"""


def user_db_error(exc, fallback="Something went wrong. Please try again."):
    """Return the user-facing message for a database exception.

    Django wraps the psycopg2 error, so the original error is usually on
    ``__cause__``. RAISE EXCEPTION from plpgsql arrives with pgcode P0001
    and its text in ``diag.message_primary``.
    """
    for candidate in (getattr(exc, "__cause__", None), exc):
        if candidate is None:
            continue
        pgcode = getattr(candidate, "pgcode", None)
        diag = getattr(candidate, "diag", None)
        message = getattr(diag, "message_primary", None) if diag else None
        if pgcode == "P0001" and message:
            return message.strip()
    return fallback
