from agent.config import load_job_preferences, load_settings


def test_load_settings() -> None:
    settings = load_settings()

    assert settings["app"]["name"] == "AI Job Application Agent"
    assert settings["automation"]["stop_before_submit"] is True


def test_load_job_preferences() -> None:
    preferences = load_job_preferences()

    assert preferences["minimum_score"] == 75
    assert "Senior Data Engineer" in preferences["preferred_roles"]
    assert preferences["employment"]["w2_only"] is True
