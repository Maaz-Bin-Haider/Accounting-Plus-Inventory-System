import logging

from django.http import JsonResponse


logger = logging.getLogger(__name__)


def internal_server_error(exception):
    """Log an unexpected exception without exposing its details to the client."""
    logger.exception("Unhandled endpoint error", exc_info=exception)
    return JsonResponse(
        {"error": "An internal server error occurred."},
        status=500,
    )
