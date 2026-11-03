import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError

import app as aura


class LoginTests(unittest.TestCase):
    def setUp(self):
        aura.app.config.update(TESTING=True)
        self.client = aura.app.test_client()

    def submit_login(self):
        self.client.get("/login")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["_csrf_token"]
        return self.client.post(
            "/login",
            data={
                "csrf_token": csrf_token,
                "email": "person@example.com",
                "password": "correct-password",
            },
        )

    def mock_auth_client(self, *, response=None, error=None):
        auth_client = Mock()
        if error is not None:
            auth_client.auth.sign_in_with_password.side_effect = error
        else:
            auth_client.auth.sign_in_with_password.return_value = response
        return auth_client

    def test_confirmed_user_gets_session_and_returns_to_homepage(self):
        user = SimpleNamespace(
            id="user-123",
            email="person@example.com",
            user_metadata={"username": "AuraUser"},
        )
        auth_client = self.mock_auth_client(
            response=SimpleNamespace(user=user, session=object())
        )

        with patch("app.supabase_client", return_value=auth_client):
            response = self.submit_login()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_id"], "user-123")
            self.assertEqual(browser_session["username"], "AuraUser")
            self.assertEqual(browser_session["email"], "person@example.com")
        homepage = self.client.get("/")
        self.assertIn(b">AuraUser</a>", homepage.data)
        self.assertIn(b"Welcome, AuraUser", homepage.data)
        self.assertIn(b"Log out", homepage.data)
        self.assertNotIn(b"Sign in", homepage.data)
        self.assertNotIn(b"Create an account", homepage.data)
        self.assertNotIn(b'class="welcome-overlay"', homepage.data)
        auth_client.auth.sign_in_with_password.assert_called_once_with(
            {"email": "person@example.com", "password": "correct-password"}
        )

    def test_existing_authenticated_user_is_redirected_from_login(self):
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = "user-123"
            browser_session["username"] = "AuraUser"

        response = self.client.get("/login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_invalid_credentials_show_accurate_message(self):
        errors = (
            AuthInvalidCredentialsError("Invalid login credentials"),
            AuthApiError("Invalid login credentials", 400, "invalid_credentials"),
        )
        for error in errors:
            with self.subTest(error_type=type(error).__name__):
                auth_client = self.mock_auth_client(error=error)
                with patch("app.supabase_client", return_value=auth_client):
                    response = self.submit_login()

                self.assertIn("error=invalid", response.location)
                page = self.client.get(response.location)
                self.assertIn(b"Email or password is incorrect.", page.data)

    def test_unconfirmed_email_has_a_separate_message(self):
        auth_client = self.mock_auth_client(
            error=AuthApiError("Email not confirmed", 400, "email_not_confirmed")
        )

        with patch("app.supabase_client", return_value=auth_client):
            response = self.submit_login()

        self.assertIn("error=unconfirmed", response.location)
        page = self.client.get(response.location)
        self.assertIn(b"Please confirm your email address", page.data)

    def test_supabase_service_failure_has_a_separate_message(self):
        auth_client = self.mock_auth_client(
            error=httpx.ConnectError("Supabase is unreachable")
        )

        with patch("app.supabase_client", return_value=auth_client):
            response = self.submit_login()

        self.assertIn("error=service", response.location)
        page = self.client.get(response.location)
        self.assertIn(b"Sign-in is temporarily unavailable", page.data)

    def test_missing_session_for_unconfirmed_user_shows_confirmation_message(self):
        user = SimpleNamespace(
            id="user-123",
            email="person@example.com",
            user_metadata={},
            email_confirmed_at=None,
            confirmed_at=None,
        )
        auth_client = self.mock_auth_client(
            response=SimpleNamespace(user=user, session=None)
        )

        with patch("app.supabase_client", return_value=auth_client):
            response = self.submit_login()

        self.assertIn("error=unconfirmed", response.location)


if __name__ == "__main__":
    unittest.main()
