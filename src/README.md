# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher sign-in to register and unregister students
- Public view of activities and registered students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. From the repository root, create a teacher account in the checked-in
   credential file:

   ```
   python src/create_teacher.py
   ```

   The command prompts for a username and password, then stores a salted
   PBKDF2 hash in `src/teachers.json`; it never writes the plaintext password.
   The file starts empty, so configure at least one teacher before signing in.
   Use a strong password because the hashes are kept with the application code.

3. From the `src` directory, run the application:

   ```
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - Activities website: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                              | Description                                           |
| ------ | --------------------------------------------------------------------- | ----------------------------------------------------- |
| GET    | `/activities`                                                         | Get all activities and registered students            |
| POST   | `/auth/login`                                                         | Sign in; sets an HTTP-only session cookie              |
| GET    | `/auth/session`                                                       | Check the current teacher session                     |
| POST   | `/auth/logout`                                                        | End the current teacher session                       |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu`     | Register a student (teacher session required)          |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)       |

Teacher sessions are held in memory and expire after eight hours. Restarting
the app invalidates active sessions. Serve the app over HTTPS outside local
development so the session cookie is always protected in transit.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
