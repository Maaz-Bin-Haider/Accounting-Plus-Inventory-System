from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AuthenticationViewTests(TestCase):
    """Lock down the public authentication contract used by the frontend."""

    @classmethod
    def setUpTestData(cls):
        cls.username = "ci-test-user"
        cls.password = "A-strong-test-password-493!"
        cls.user = get_user_model().objects.create_user(
            username=cls.username, password=cls.password
        )

    def test_login_page_is_public(self):
        response = self.client.get(reverse("authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication_templates/login_template.html")

    def test_login_rejects_missing_credentials(self):
        response = self.client.post(reverse("authentication:login"), {})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            "status": "error",
            "message": "Please enter both username and password.",
        })

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(reverse("authentication:login"), {
            "username": self.username, "password": "incorrect",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")

    def test_login_creates_authenticated_session(self):
        response = self.client.post(reverse("authentication:login"), {
            "username": self.username, "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("authentication:login"))
        self.assertRedirects(response, reverse("home:home"))

    def test_current_user_requires_login(self):
        response = self.client.get(reverse("authentication:current_user"))
        login = reverse("authentication:login")
        current = reverse("authentication:current_user")
        self.assertRedirects(response, f"{login}?next={current}")

    def test_current_user_returns_session_username(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("authentication:current_user"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"username": self.username})

    def test_logout_clears_session(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("authentication:logout"))
        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse("authentication:login"), {
            "username": self.username, "password": self.password,
        })
        self.assertEqual(response.status_code, 403)
