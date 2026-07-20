from unittest.mock import Mock

from django.test import SimpleTestCase

from financee.db_errors import user_db_error


class UserDatabaseErrorTests(SimpleTestCase):
    def test_curated_postgres_exception_is_safe_to_display(self):
        cause = Mock()
        cause.pgcode = "P0001"
        cause.diag.message_primary = "  Serial is already sold.  "
        wrapper = Exception("internal wrapper details")
        wrapper.__cause__ = cause
        self.assertEqual(user_db_error(wrapper), "Serial is already sold.")

    def test_non_curated_database_error_uses_fallback(self):
        error = Mock()
        error.pgcode = "23505"
        error.diag.message_primary = "sensitive unique constraint details"
        self.assertEqual(
            user_db_error(error, "Unable to save the record."),
            "Unable to save the record.",
        )

    def test_plain_exception_uses_default_fallback(self):
        self.assertEqual(
            user_db_error(RuntimeError("connection details")),
            "Something went wrong. Please try again.",
        )

