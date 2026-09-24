from auth.session_auth import create_session_token, validate_session_token


def test_persistent_session_token_survives_new_session():
    token = create_session_token("admin", "secret-password", now=1_000, max_age_seconds=300)
    assert validate_session_token(token, "admin", "secret-password", now=1_001)
    assert validate_session_token(token, "admin", "secret-password", now=1_299)


def test_persistent_session_token_expires():
    token = create_session_token("admin", "secret-password", now=1_000, max_age_seconds=300)
    assert not validate_session_token(token, "admin", "secret-password", now=1_300)


def test_persistent_session_token_invalidates_when_credentials_change():
    token = create_session_token("admin", "secret-password", now=1_000, max_age_seconds=300)
    assert not validate_session_token(token, "admin", "changed-password", now=1_100)
    assert not validate_session_token(token, "other-user", "secret-password", now=1_100)


def test_tampered_session_token_is_rejected():
    token = create_session_token("admin", "secret-password", now=1_000, max_age_seconds=300)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert not validate_session_token(tampered, "admin", "secret-password", now=1_100)
