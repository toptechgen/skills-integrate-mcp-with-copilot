"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PASSWORD_HASH_ITERATIONS = 600_000
SESSION_COOKIE = "teacher_session"
SESSION_MAX_AGE = 8 * 60 * 60
TEACHERS_FILE = Path(__file__).with_name("teachers.json")

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


def load_teachers() -> dict[str, str]:
    try:
        with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
            data = json.load(teachers_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Unable to load teacher credentials from {TEACHERS_FILE}"
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise RuntimeError("Teacher credentials must contain a 'teachers' list")

    teachers = {}
    for teacher in data["teachers"]:
        if not isinstance(teacher, dict):
            raise RuntimeError("Each teacher credential must be an object")

        username = teacher.get("username")
        password_hash = teacher.get("password_hash")
        if not isinstance(username, str) or not username.strip():
            raise RuntimeError("Each teacher must have a non-empty username")
        if username in teachers:
            raise RuntimeError(f"Duplicate teacher username: {username}")
        if not isinstance(password_hash, str):
            raise RuntimeError(f"Missing password hash for teacher: {username}")

        parts = password_hash.split("$")
        try:
            valid_hash = (
                len(parts) == 4
                and parts[0] == "pbkdf2_sha256"
                and int(parts[1]) == PASSWORD_HASH_ITERATIONS
                and len(bytes.fromhex(parts[2])) >= 16
                and len(bytes.fromhex(parts[3])) == 32
            )
        except ValueError:
            valid_hash = False
        if not valid_hash:
            raise RuntimeError(f"Invalid password hash for teacher: {username}")

        teachers[username] = password_hash

    return teachers


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


teachers = load_teachers()
active_sessions: dict[str, tuple[str, float]] = {}
DUMMY_PASSWORD_HASH = hash_password("invalid-password", b"\0" * 16)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


def require_teacher(
    teacher_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> None:
    username = get_session_username(teacher_session)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")


def get_session_username(teacher_session: Optional[str]) -> Optional[str]:
    if not teacher_session:
        return None
    session = active_sessions.get(teacher_session)
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= time.time():
        active_sessions.pop(teacher_session, None)
        return None
    return username


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    stored_hash = password_hash or DUMMY_PASSWORD_HASH
    _, iterations, salt_hex, digest_hex = stored_hash.split("$")
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    matches = hmac.compare_digest(candidate.hex(), digest_hex)
    return password_hash is not None and matches


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def login(
    login_request: LoginRequest,
    request: Request,
    response: Response,
):
    username = login_request.username.strip()
    password_hash = teachers.get(username)
    if not verify_password(login_request.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    previous_session = request.cookies.get(SESSION_COOKIE)
    if previous_session:
        active_sessions.pop(previous_session, None)

    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = (username, time.time() + SESSION_MAX_AGE)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return {"username": username}


@app.get("/auth/session")
def get_session(
    teacher_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    return {"username": get_session_username(teacher_session)}


@app.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    teacher_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    if teacher_session:
        active_sessions.pop(teacher_session, None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return {"message": "Logged out"}


@app.post(
    "/activities/{activity_name}/signup",
    dependencies=[Depends(require_teacher)],
)
def signup_for_activity(
    activity_name: str,
    email: str,
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(require_teacher)],
)
def unregister_from_activity(
    activity_name: str,
    email: str,
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
