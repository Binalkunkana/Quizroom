# Quiz system starter

Simple Django server-rendered starter using MySQL and Django admin. The custom user model is configured before the first migration.

## Folder structure

```text
quiz_system/
├── manage.py
├── requirements.txt
├── myproject/             # settings and root URLs
├── users/                 # custom user and ADMIN/FACULTY/STUDENT roles
├── courses/               # courses and student enrollment
├── questions/             # MCQ/written questions and choices
├── quizzes/               # quizzes and ordered question assignments
└── grading/               # attempts, submitted answers, grading helper
```

## Start with MySQL

Create an empty database named `quiz_db` in MySQL. Install dependencies in the project's virtual environment, then set your connection details in PowerShell:

```powershell
.\myenv\Scripts\python.exe -m pip install -r requirements.txt
$env:DB_NAME = "quiz_db"
$env:DB_USER = "root"
$env:DB_PASSWORD = "your_mysql_password"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
.\myenv\Scripts\python.exe manage.py makemigrations users courses questions quizzes grading
.\myenv\Scripts\python.exe manage.py migrate
.\myenv\Scripts\python.exe manage.py createsuperuser
.\myenv\Scripts\python.exe manage.py runserver
```

Open `/admin/` and sign in with the superuser, or use the server-rendered pages under `/accounts/`, `/courses/`, `/questions/`, `/quizzes/`, and `/grading/`. Admins can create users at `/accounts/create/`; faculty can create courses and questions, assemble quizzes, and publish them. Students can view all courses and take any published quiz; they can see results after faculty releases them. Login/logout use Django sessions; a superuser is assigned the ADMIN role automatically.

`grading.services.grade_objective_answers(attempt)` grades MCQ answers. Written answers remain ungraded for faculty; the attempt becomes fully graded after those answers are scored. Release results by setting `is_released` in admin.

This is a learning starter, not production-ready. OTP/Google sign-in, timers enforced on the server, attempt limits, and API permission rules are separate next steps; don't expose answer keys in a student-facing endpoint. The starter's role checks are in the views, while Django admin has its own staff permissions.
