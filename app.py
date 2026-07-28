from pathlib import Path

from agent.config import load_job_preferences, load_settings
from agent.database import initialize_database
APP_NAME = "AI Job Application Agent"


def ensure_directories() -> None:
    for folder in ("data", "logs", "outputs"):
        Path(folder).mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_directories()
    initialize_database()

    settings = load_settings()
    preferences = load_job_preferences()

    print(f"{settings['app']['name']} is ready.")
    print(f"Environment: {settings['app']['environment']}")
    print(f"Minimum job score: {preferences['minimum_score']}")
    print(
        "Preferred roles: "
        + ", ".join(preferences["preferred_roles"])
    )


if __name__ == "__main__":
    main()
code .
python app.py
