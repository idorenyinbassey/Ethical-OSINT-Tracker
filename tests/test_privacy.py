"""PII scoping and data retention (Issue #15)."""
from datetime import datetime, timedelta

from app.repositories.investigation_repository import (
    create_investigation,
    list_recent,
    count_all,
    purge_old_investigations,
)


def test_list_recent_scoped_to_user(app, user_a, user_b):
    with app.app_context():
        create_investigation("email", "a-target@example.com", "{}", user_id=user_a.id)
        create_investigation("email", "b-target@example.com", "{}", user_id=user_b.id)

        a_recent = list_recent(50, user_id=user_a.id)
        a_queries = {inv.query for inv in a_recent}
        assert "a-target@example.com" in a_queries
        assert "b-target@example.com" not in a_queries  # no cross-user PII leak


def test_count_all_scoped_to_user(app, user_a, user_b):
    with app.app_context():
        before_a = count_all(user_id=user_a.id)
        create_investigation("ip", "1.2.3.4", "{}", user_id=user_a.id)
        after_a = count_all(user_id=user_a.id)
        assert after_a == before_a + 1


def test_purge_old_investigations_deletes_stale(app, user_a):
    with app.app_context():
        inv = create_investigation("ip", "9.9.9.9", "{}", user_id=user_a.id)
        # Backdate it beyond the retention window.
        from app.db import get_session
        from app.models.investigation import Investigation
        session = get_session()
        try:
            row = session.get(Investigation, inv.id)
            row.created_at = datetime.utcnow() - timedelta(days=400)
            session.add(row)
            session.commit()
        finally:
            session.close()

        deleted = purge_old_investigations(retention_days=90)
        assert deleted >= 1


def test_purge_disabled_when_non_positive(app):
    with app.app_context():
        assert purge_old_investigations(retention_days=0) == 0
        assert purge_old_investigations(retention_days=-5) == 0
