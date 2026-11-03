import unittest
from unittest.mock import Mock, patch

import app as aura


class QuizRetakeTests(unittest.TestCase):
    def setUp(self):
        aura.app.config.update(TESTING=True)
        self.client = aura.app.test_client()

    def test_result_links_to_same_quiz_and_retake_starts_blank(self):
        previous_result = {"type": "phone_addiction", "score": 21}
        with self.client.session_transaction() as browser_session:
            browser_session["quiz_result"] = previous_result
            browser_session["user_id"] = "user-123"

        result_page = self.client.get("/quiz/results")

        self.assertIn(b'href="/quiz/phone_addiction">Retake this check-in</a>', result_page.data)
        retake_page = self.client.get("/quiz/phone_addiction")
        self.assertEqual(retake_page.status_code, 200)
        self.assertNotIn(b"checked", retake_page.data)
        self.assertIn(b'name="csrf_token"', retake_page.data)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["quiz_result"], previous_result)
            self.assertEqual(browser_session["user_id"], "user-123")

    def test_retake_keeps_csrf_validation_and_appends_signed_in_result(self):
        previous_result = {"type": "anxiety", "score": 18}
        csrf_token = "test-csrf-token"
        with self.client.session_transaction() as browser_session:
            browser_session["quiz_result"] = previous_result
            browser_session["user_id"] = "user-123"
            browser_session["_csrf_token"] = csrf_token

        answers = {f"q{number}": "2" for number in range(1, 11)}
        self.assertEqual(self.client.post("/quiz/anxiety", data=answers).status_code, 400)

        incomplete = self.client.post(
            "/quiz/anxiety", data={"csrf_token": csrf_token, "q1": "2"}
        )
        self.assertIn("error=incomplete", incomplete.location)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["quiz_result"], previous_result)

        saved_results = [{"user_id": "user-123", "quiz_type": "anxiety", "score": 18}]
        admin_client = Mock()
        admin_client.table.return_value.insert.side_effect = (
            lambda result: saved_results.append(result)
        )
        with patch("app.supabase_admin_client", return_value=admin_client):
            response = self.client.post(
                "/quiz/anxiety", data={"csrf_token": csrf_token, **answers}
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            saved_results,
            [
                {"user_id": "user-123", "quiz_type": "anxiety", "score": 18},
                {"user_id": "user-123", "quiz_type": "anxiety", "score": 20},
            ],
        )
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["quiz_result"], {"type": "anxiety", "score": 20})


if __name__ == "__main__":
    unittest.main()
