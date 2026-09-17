"""app.repositories.api_key_repository — creation, hashing, revocation."""
from app.repositories.api_key_repository import (
    create_api_key, list_active_keys, get_by_key_hash, get_by_raw_key,
    revoke_key, touch_last_used, _hash,
)


def test_create_returns_raw_key_once_and_stores_only_hash(app, user_a):
    with app.app_context():
        key, raw = create_api_key(user_a.id, label="test")
        assert raw.startswith("osint_")
        assert key.key_hash == _hash(raw)
        assert key.key_hash != raw  # never store the raw key itself


def test_get_by_raw_key_round_trips(app, user_a):
    with app.app_context():
        key, raw = create_api_key(user_a.id, label="test")
        found = get_by_raw_key(raw)
        assert found is not None
        assert found.id == key.id


def test_get_by_raw_key_wrong_key_returns_none(app, user_a):
    with app.app_context():
        create_api_key(user_a.id, label="test")
        assert get_by_raw_key("osint_totally-wrong-value") is None


def test_list_active_keys_excludes_revoked(app, user_a):
    with app.app_context():
        key1, _ = create_api_key(user_a.id, label="one")
        key2, _ = create_api_key(user_a.id, label="two")
        revoke_key(key1.id, user_id=user_a.id)
        active = list_active_keys(user_a.id)
        ids = {k.id for k in active}
        assert key1.id not in ids
        assert key2.id in ids


def test_revoked_key_stays_findable_by_hash_but_marked_revoked(app, user_a):
    with app.app_context():
        key, raw = create_api_key(user_a.id)
        revoke_key(key.id, user_id=user_a.id)
        found = get_by_key_hash(_hash(raw))
        assert found is not None
        assert found.revoked is True


def test_revoke_requires_ownership(app, user_a, user_b):
    with app.app_context():
        key, _ = create_api_key(user_a.id)
        assert revoke_key(key.id, user_id=user_b.id) is False
        assert revoke_key(key.id, user_id=user_a.id) is True


def test_touch_last_used_sets_timestamp(app, user_a):
    with app.app_context():
        key, _ = create_api_key(user_a.id)
        assert key.last_used_at is None
        touch_last_used(key.id)
        refreshed = get_by_key_hash(key.key_hash)
        assert refreshed.last_used_at is not None
