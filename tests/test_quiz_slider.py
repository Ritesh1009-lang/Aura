import re
import unittest

import app as aura


class QuizSliderTests(unittest.TestCase):
    def setUp(self):
        aura.app.config.update(TESTING=True)
        self.client = aura.app.test_client()

    def test_quiz_renders_question_cards_navigation_and_progress(self):
        response = self.client.get("/quiz/anxiety")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question 1 of 10", response.data)
        self.assertIn(b"quiz-previous", response.data)
        self.assertIn(b"quiz-next", response.data)
        self.assertIn(b"Alt + Left/Right", response.data)
        self.assertEqual(len(re.findall(rb'class="checkin-question"', response.data)), 10)
        self.assertEqual(len(re.findall(rb'name="q\d+"', response.data)), 40)
        self.assertNotIn(b" checked", response.data)

    def test_server_rejects_incomplete_and_out_of_range_answers(self):
        page = self.client.get("/quiz/anxiety")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["_csrf_token"]

        incomplete = self.client.post(
            "/quiz/anxiety",
            data={"csrf_token": csrf_token, "q1": "1"},
        )
        self.assertIn("error=incomplete", incomplete.location)

        invalid_answers = {f"q{number}": "2" for number in range(1, 11)}
        invalid_answers["q3"] = "5"
        invalid = self.client.post(
            "/quiz/anxiety",
            data={"csrf_token": csrf_token, **invalid_answers},
        )
        self.assertIn("error=invalid", invalid.location)
        self.assertEqual(page.status_code, 200)


if __name__ == "__main__":
    unittest.main()
