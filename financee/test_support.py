"""Reusable helpers for Financee endpoint tests."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class UserPermissionTestMixin:
    """Create test users and grant the custom ``auth`` permissions used by views."""

    test_password = "A-strong-test-password-493!"

    @classmethod
    def create_test_user(cls, username="test-user", **overrides):
        values = {"username": username, "password": cls.test_password}
        values.update(overrides)
        return get_user_model().objects.create_user(**values)

    @staticmethod
    def ensure_auth_permission(codename, name=None):
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name or codename.replace("_", " ").title()},
        )
        return permission

    @classmethod
    def grant_permissions(cls, user, *codenames):
        permissions = [cls.ensure_auth_permission(code) for code in codenames]
        user.user_permissions.add(*permissions)
        # Clear Django's per-user permission cache if this user was checked before.
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            user.__dict__.pop(attribute, None)
        return user

