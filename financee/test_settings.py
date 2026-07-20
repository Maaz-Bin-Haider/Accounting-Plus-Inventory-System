"""Settings used exclusively by automated Django tests.

Run with::

    DJANGO_SETTINGS_MODULE=financee.test_settings python manage.py test

The module fails closed unless TEST_DB_NAME is explicitly provided and uses the
``financee_test_`` prefix. This protects the production database from an
incorrect local or CI command.
"""

import os

from .settings import *  # noqa: F403


TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "").strip()
TEST_DB_HOST = os.environ.get("TEST_DB_HOST", "localhost").strip()
TEST_DB_USER = os.environ.get("TEST_DB_USER", "postgres").strip()
TEST_DB_PASSWORD = os.environ.get("TEST_DB_PASSWORD", "")
TEST_DB_PORT = os.environ.get("TEST_DB_PORT", "5432").strip()
TEST_DB_MAINTENANCE_NAME = os.environ.get(
    "TEST_DB_MAINTENANCE_NAME", "postgres"
).strip()

if not TEST_DB_NAME:
    raise RuntimeError(
        "TEST_DB_NAME is required. Use a disposable name beginning with "
        "'financee_test_'."
    )

if not TEST_DB_NAME.startswith("financee_test_"):
    raise RuntimeError("Refusing to run tests: TEST_DB_NAME must start with 'financee_test_'.")

production_name = os.environ.get("DB_NAME", "").strip()
if production_name and TEST_DB_NAME == production_name:
    raise RuntimeError("Refusing to run tests against the configured production database.")

blocked_hosts = {
    "13.232.33.250",
    "swisstechfinance.com",
    "www.swisstechfinance.com",
}
if TEST_DB_HOST.lower() in blocked_hosts:
    raise RuntimeError("Refusing to run tests against a production host.")

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Connect here before Django creates the guarded database in TEST.NAME.
        "NAME": TEST_DB_MAINTENANCE_NAME,
        "USER": TEST_DB_USER,
        "PASSWORD": TEST_DB_PASSWORD,
        "HOST": TEST_DB_HOST,
        "PORT": TEST_DB_PORT,
        "CONN_MAX_AGE": 0,
        "TEST": {
            # Use the exact guarded name. Django may create and destroy it.
            "NAME": TEST_DB_NAME,
        },
    }
}

# Tests must never depend on an external Redis instance or share cached state.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "financee-automated-tests",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
