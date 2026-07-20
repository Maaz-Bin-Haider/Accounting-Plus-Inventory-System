from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_checks_database_and_cache(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(cache.get("financee:health-check"), "ok")

    def test_health_rejects_non_get_methods(self):
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)

    @patch("financee.health.connection")
    def test_health_failure_is_generic(self, connection):
        connection.cursor.side_effect = RuntimeError("secret database hostname")
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy"})
        self.assertNotContains(response, "secret database hostname", status_code=503)
