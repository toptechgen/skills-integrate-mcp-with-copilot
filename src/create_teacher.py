import getpass
import json
from pathlib import Path

from app import TEACHERS_FILE, hash_password


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty")

    password = getpass.getpass("Teacher password: ")
    if not password:
        raise ValueError("Password cannot be empty")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")

    with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
        data = json.load(teachers_file)

    existing = data.get("teachers")
    if not isinstance(existing, list):
        raise ValueError("Teacher credentials must contain a 'teachers' list")
    if any(teacher.get("username") == username for teacher in existing):
        raise ValueError(f"Teacher username already exists: {username}")

    existing.append({"username": username, "password_hash": hash_password(password)})
    TEACHERS_FILE.write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Added teacher {username} to {Path(TEACHERS_FILE)}")


if __name__ == "__main__":
    main()
