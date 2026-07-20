from django.conf import settings
from django.core.cache import cache, caches
from django.test import SimpleTestCase
from redis import Redis


class RedisCacheIntegrationTests(SimpleTestCase):
    """Exercise Django's cache contract against the disposable Redis service."""

    key_prefix = "financee:integration-test"

    def setUp(self):
        if not settings.TEST_REDIS_URL:
            self.skipTest("TEST_REDIS_URL is not configured")
        cache.clear()
        self.redis = Redis.from_url(settings.TEST_REDIS_URL)

    def tearDown(self):
        if hasattr(self, "redis"):
            cache.clear()
            self.redis.close()

    def redis_key(self, suffix):
        matches = list(self.redis.scan_iter(match=f"*{self.key_prefix}:{suffix}"))
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_redis_backend_round_trip_across_cache_clients(self):
        cache.set(f"{self.key_prefix}:round-trip", {"status": "ok"}, timeout=30)
        independent_cache = caches.create_connection("default")

        self.assertEqual(
            independent_cache.get(f"{self.key_prefix}:round-trip"),
            {"status": "ok"},
        )
        self.assertEqual(self.redis.type(self.redis_key("round-trip")), b"string")

    def test_timeout_reaches_redis_and_expired_value_is_not_returned(self):
        key = f"{self.key_prefix}:ttl"
        cache.set(key, "temporary", timeout=30)
        raw_key = self.redis_key("ttl")

        ttl = self.redis.ttl(raw_key)
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 30)
        self.redis.expire(raw_key, 0)
        self.assertIsNone(cache.get(key))
