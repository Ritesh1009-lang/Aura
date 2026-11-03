"""Aura's self-contained Flask application.

Run with: .venv\\Scripts\\python app.py
"""

import os
import re
import secrets
from datetime import date

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
import httpx
from supabase import create_client
from supabase_auth.errors import AuthError, AuthInvalidCredentialsError

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

# Standard Flask layout: HTML lives in templates/ and public assets in static/.
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("AURA_SECRET_KEY") or secrets.token_urlsafe(32)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def verify_csrf():
    if request.method != "POST":
        return
    supplied_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not supplied_token or not secrets.compare_digest(supplied_token, session.get("_csrf_token", "")):
        abort(400, "Invalid form security token. Refresh the page and try again.")

def supabase_client():
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("Supabase is not configured. Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY to .env.")
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


def supabase_admin_client():
    if not SUPABASE_SECRET_KEY:
        raise RuntimeError("SUPABASE_SECRET_KEY is required for secure server-side result storage.")
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def login_error_code(error):
    error_code = str(getattr(error, "code", "") or "").lower()
    error_message = str(getattr(error, "message", error)).lower()
    if isinstance(error, AuthInvalidCredentialsError) or error_code == "invalid_credentials" or "invalid login credentials" in error_message:
        return "invalid"
    if error_code in {"email_not_confirmed", "email_not_verified"} or "email not confirmed" in error_message:
        return "unconfirmed"
    return "service"


RESPONSES = {
    "hello": "Hi there. How can I help you?",
    "sad": "I'm sorry you're having a hard time. Would you like to share a little more?",
    "anxious": "Try a slow breath: in for 4, hold for 4, out for 4. You're not alone.",
    "stressed": "Stress can feel heavy. Could you take one small break or focus on the next step only?",
    "lonely": "I'm here with you. Reaching out to someone you trust can help too.",
    "panic attack": "Try naming 5 things you see, 4 you feel, 3 you hear, 2 you smell, and 1 you taste.",
    "thank you": "You're welcome. Please be kind to yourself today.",
    "bye": "Take care. You deserve support.",
}


def get_chat_response(message, history):
    """Return a supportive, bounded response using the current message and recent chat context."""
    message_lower = message.lower()
    previous_user = next((item["content"].lower() for item in reversed(history) if item.get("role") == "user"), "")
    crisis_terms = ("suicide", "kill myself", "self harm", "hurt myself", "don't want to do this anymore", "dont want to do this anymore", "do not want to do this anymore", "end it all", "want to die")
    if any(term in message_lower for term in crisis_terms):
        return "I’m really glad you told me. When you say you don’t want to do this anymore, are you thinking about hurting yourself or ending your life right now? If you might act on those thoughts, call your local emergency number now or go to the nearest emergency department. If you can, contact someone you trust and ask them to stay with you."
    if any(term in message_lower for term in ("anxious", "anxiety", "worried", "panic", "nervous")):
        return "That sounds like a lot to carry. For the next minute, try putting both feet on the floor and breathing out a little longer than you breathe in—inhale for 4, exhale for 6. Then choose just one thing you can control in the next ten minutes. What is making the anxiety feel strongest right now?"
    if any(term in message_lower for term in ("sad", "cry", "depressed", "hopeless", "alone", "lonely", "empty")):
        return "I’m sorry this feels so heavy. You do not need to fix the whole day at once. A small next step could be drinking some water, sitting near someone safe, or writing down the one thing that hurts most. Would you rather talk about what happened, or would you like a grounding exercise first?"
    if any(term in message_lower for term in ("angry", "mad", "frustrated", "annoyed")):
        return "That sounds frustrating, and it makes sense that you need some space with it. Before you react, try a short reset: step away, unclench your shoulders, and name the one part that feels most unfair. Is this anger about something that just happened, or has it been building for a while?"
    if any(term in message_lower for term in ("sleep", "insomnia", "tired", "exhausted")):
        return "Being tired can make every feeling louder. If sleep is difficult tonight, aim for a gentler wind-down: dim the screen, have a sip of water, and try a few slow breaths rather than forcing sleep. Has your mind been racing, or is something else keeping you awake?"
    if any(term in message_lower for term in ("stress", "overwhelmed", "too much", "pressure")):
        return "It sounds like there is too much competing for your attention. Try writing down everything that is pulling at you, then circle only the next smallest action—not the whole solution. What is the one task or worry that feels most urgent?"
    if message_lower in {"yes", "yeah", "yep", "no", "nope", "not really"} and previous_user:
        return "Thank you for answering. I want to make sure I understand rather than assume—could you tell me a little more about what feels hardest for you right now?"
    if any(term in message_lower for term in ("thank", "thanks")):
        return "You’re welcome. I’m glad you reached out. Before you go, what is one small kind thing you could do for yourself in the next few minutes?"
    return "I’m listening. It sounds like this matters to you, and you do not have to put it perfectly into words. What happened, and how is it affecting you right now?"

QUIZZES = {
    "anxiety": ["How often do you feel nervous or anxious?", "Do you experience excessive worry about everyday situations?", "Do you have trouble concentrating due to anxiety?", "Do you feel restless or on edge?", "Do you experience physical symptoms such as a racing heart or sweating?", "Do you avoid situations that make you anxious?", "Do you have trouble sleeping due to anxiety?", "Do you feel irritable or easily agitated?", "Do you experience panic attacks?", "Do you feel overwhelmed by your worries?"],
    "depression": ["How often do you feel sad or down?", "Do you have trouble sleeping or sleep too much?", "Do you feel tired or lack energy?", "Do you have difficulty concentrating or making decisions?", "Do you lose interest in activities you used to enjoy?", "Do you feel worthless or guilty?", "Do you experience changes in appetite or weight?", "Do you feel restless or slowed down?", "Do you have thoughts of self-harm or suicide?", "Do you feel hopeless about the future?"],
    "phone_addiction": ["How often do you check your phone within an hour?", "Do you feel anxious without your phone?", "How long do you spend on social media daily?", "Do you use your phone during meals?", "Do you use your phone right before sleeping?", "Do you ignore people to use your phone?", "Do you feel the need to immediately respond to notifications?", "Do you lose track of time while using your phone?", "Do you use your phone while walking?", "Do you feel uncomfortable without your phone?"],
    "fear": ["How often do you feel afraid or scared?", "Do you avoid situations that make you fearful?", "Do you experience physical symptoms like trembling or sweating when afraid?", "Do you feel paralyzed or unable to act when fearful?", "Do you have recurring nightmares or intrusive thoughts about your fears?", "Do you feel a sense of dread or impending doom?", "Do you feel your fears are irrational or exaggerated?", "Do you feel your fears interfere with daily life?", "Do you feel the need to constantly check for safety or reassurance?", "Do you feel your fears are out of your control?"],
}


@app.get("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") and session.get("username"):
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    try:
        auth_response = supabase_client().auth.sign_in_with_password({"email": email, "password": password})
    except AuthError as error:
        return redirect(url_for("login", error=login_error_code(error)))
    except (httpx.HTTPError, RuntimeError):
        return redirect(url_for("login", error="service"))
    user = getattr(auth_response, "user", None)
    auth_session = getattr(auth_response, "session", None)
    if user is None or auth_session is None:
        if user is not None and not (getattr(user, "email_confirmed_at", None) or getattr(user, "confirmed_at", None)):
            return redirect(url_for("login", error="unconfirmed"))
        return redirect(url_for("login", error="service"))
    user_metadata = user.user_metadata or {}
    session.clear()
    session["username"] = user_metadata.get("username", email.split("@", 1)[0])
    session["user_id"] = str(user.id)
    session["email"] = user.email
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    phone_country = request.form.get("phone_country", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    dob = request.form.get("dob", "").strip()
    age = request.form.get("age", "").strip()
    try:
        birth_date = date.fromisoformat(dob)
        calculated_age = date.today().year - birth_date.year - ((date.today().month, date.today().day) < (birth_date.month, birth_date.day))
    except ValueError:
        calculated_age = -1
    if not username or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(password) < 8 or password != confirm_password or not age.isdigit() or int(age) != calculated_age or calculated_age < 13 or not phone_country or not re.fullmatch(r"[0-9 ()+-]{6,20}", phone_number):
        return redirect(url_for("register", error="invalid"))
    try:
        supabase_client().auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"username": username, "age": int(age), "date_of_birth": dob, "phone_country": phone_country, "phone_number": phone_number},
                "email_redirect_to": f"{APP_BASE_URL}/login?confirmed=1",
            },
        })
    except Exception as error:
        error_code = "exists" if "already registered" in str(error).lower() else "service"
        return redirect(url_for("register", error=error_code))
    return redirect(url_for("login", registered="1"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        try:
            supabase_client().auth.reset_password_for_email(email, {"redirect_to": f"{APP_BASE_URL}/reset-password"})
        except Exception:
            # Keep the same message to avoid account enumeration.
            pass
        return redirect(url_for("forgot_password", sent="1"))
    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        return render_template("reset_password.html")
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    access_token = str(payload.get("access_token", ""))
    refresh_token = str(payload.get("refresh_token", ""))
    if len(password) < 8 or not access_token or not refresh_token:
        return jsonify(error="Use a password with at least 8 characters."), 400
    try:
        client = supabase_client()
        client.auth.set_session(access_token, refresh_token)
        client.auth.update_user({"password": password})
    except Exception:
        return jsonify(error="This reset link is invalid or expired. Please request a new one."), 400
    return jsonify(ok=True)


@app.get("/welcome")
def welcome():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("welcome.html", username=session["username"])


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify(error="Please enter a message."), 400
    raw_history = payload.get("history", [])
    history = [{"role": item.get("role"), "content": str(item.get("content", ""))[:500]} for item in raw_history[-8:] if isinstance(item, dict) and item.get("role") in {"user", "assistant"}]
    response = get_chat_response(message, history)
    return jsonify(response=response)


@app.route("/quiz/<quiz_type>", methods=["GET", "POST"])
def quiz(quiz_type):
    questions = QUIZZES.get(quiz_type)
    if not questions:
        return redirect(url_for("home"))
    if request.method == "POST":
        try:
            answers = [int(request.form[f"q{number}"]) for number in range(1, 11)]
        except (KeyError, ValueError):
            return redirect(url_for("quiz", quiz_type=quiz_type, error="incomplete"))
        if any(answer not in (1, 2, 3, 4) for answer in answers):
            return redirect(url_for("quiz", quiz_type=quiz_type, error="invalid"))
        session["quiz_result"] = {"type": quiz_type, "score": sum(answers)}
        if "user_id" in session:
            try:
                supabase_admin_client().table("quiz_results").insert({"user_id": session["user_id"], "quiz_type": quiz_type, "score": sum(answers)}).execute()
            except Exception:
                # A check-in should still show its result if persistence is temporarily unavailable.
                pass
        return redirect(url_for("quiz_result"))
    return render_template("quiz.html", title=quiz_type.replace("_", " ").title(), questions=questions, error=request.args.get("error"))


@app.get("/quiz/results")
def quiz_result():
    result = session.get("quiz_result")
    if not result:
        return redirect(url_for("home"))
    score = result["score"]
    level = "low" if score <= 15 else "moderate" if score <= 27 else "high"
    return render_template("quiz_result.html", title=result["type"].replace("_", " ").title(), score=score, level=level)


QUIZ_TEMPLATE = """<!doctype html><title>{{ title }} check-in | Aura</title><style>body{background:#000;color:#0ff;font:16px Arial;margin:0;padding:30px}.card{max-width:720px;margin:auto;background:#111;padding:26px;border-radius:16px;box-shadow:0 0 20px #066}a{color:#0ff}.q{border-bottom:1px solid #155;padding:16px 0}label{display:block;margin:8px 0}button{background:#0ff;border:0;padding:12px 25px;border-radius:7px;cursor:pointer;font-weight:bold}.notice{color:#ff9}</style><main class=card><a href='/'>← Back to Aura</a><h1>{{ title }} check-in</h1><p>This is a self-reflection tool, not a diagnosis.</p>{% if error %}<p class=notice>Please answer every question.</p>{% endif %}<form method=post>{% for question in questions %}{% set question_number = loop.index %}<section class=q><strong>{{ question_number }}. {{ question }}</strong>{% for value,label in [(1,'Rarely'),(2,'Sometimes'),(3,'Often'),(4,'Almost always')] %}<label><input required type=radio name='q{{ question_number }}' value='{{ value }}'> {{ label }}</label>{% endfor %}</section>{% endfor %}<button type=submit>See my result</button></form></main>"""
RESULT_TEMPLATE = """<!doctype html><title>Quiz result | Aura</title><style>body{background:#000;color:#0ff;font:18px Arial;display:grid;place-items:center;min-height:100vh;margin:0}.card{max-width:600px;text-align:center;border:2px solid #0ff;border-radius:20px;padding:40px;box-shadow:0 0 20px #0ff}a{color:#0ff;border:1px solid #0ff;padding:12px 20px;border-radius:8px;text-decoration:none;display:inline-block}</style><main class=card><h1>{{ title }} check-in</h1><h2>Score: {{ score }} / 40</h2><p>Your responses fall in the <strong>{{ level }}</strong> range for this informal check-in. It is not a diagnosis. If these feelings are affecting your life or safety, consider speaking with a qualified mental-health professional or a trusted person.</p><a href='/'>Return home</a></main>"""


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
