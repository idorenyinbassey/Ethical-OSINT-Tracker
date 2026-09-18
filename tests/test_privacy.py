"""PII scoping and data retention (Issue #15)."""
from datetime import datetime, timedelta

from app.repositories.investigation_repository import (
    create_investigation,
    list_recent,
    count_all,
    count_by_kind,
    aggregate_by_day,
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


def test_purge_spares_a_row_refreshed_after_the_cutoff(app, user_a):
    """find_or_update_recent() deliberately leaves created_at at a row's
    original first-run timestamp forever, with no age limit on matching —
    so a long-lived case's investigation that was refreshed today, but
    first created a year ago, must survive the purge. Purging on
    created_at alone would silently delete live, current data out from
    under an active case."""
    with app.app_context():
        inv = create_investigation("ip", "8.8.4.4", "{}", user_id=user_a.id)
        from app.db import get_session
        from app.models.investigation import Investigation
        session = get_session()
        try:
            row = session.get(Investigation, inv.id)
            row.created_at = datetime.utcnow() - timedelta(days=400)
            row.updated_at = datetime.utcnow()  # refreshed today
            session.add(row)
            session.commit()
        finally:
            session.close()

        purge_old_investigations(retention_days=90)

        session = get_session()
        try:
            assert session.get(Investigation, inv.id) is not None
        finally:
            session.close()


def test_purge_deletes_a_row_whose_last_update_is_still_stale(app, user_a):
    """A row that WAS refreshed, but not recently enough, is still fair
    game for the purge — coalescing to created_at only matters when
    updated_at was never set at all."""
    with app.app_context():
        inv = create_investigation("ip", "8.8.4.5", "{}", user_id=user_a.id)
        from app.db import get_session
        from app.models.investigation import Investigation
        session = get_session()
        try:
            row = session.get(Investigation, inv.id)
            row.created_at = datetime.utcnow() - timedelta(days=400)
            row.updated_at = datetime.utcnow() - timedelta(days=200)
            session.add(row)
            session.commit()
        finally:
            session.close()

        purge_old_investigations(retention_days=90)

        session = get_session()
        try:
            assert session.get(Investigation, inv.id) is None
        finally:
            session.close()


def test_count_by_kind_scoped_to_user(app, user_a, user_b):
    with app.app_context():
        create_investigation("mac", "aa:bb:cc:dd:ee:ff", "{}", user_id=user_a.id)
        create_investigation("vehicle", "1HGCM82633A004352", "{}", user_id=user_b.id)

        a_kinds = count_by_kind(user_id=user_a.id)
        assert "mac" in a_kinds
        assert "vehicle" not in a_kinds  # user B's kind is not visible to A


def test_aggregate_by_day_scoped_to_user(app, user_a, user_b):
    with app.app_context():
        create_investigation("imei", "490154203237518", "{}", user_id=user_a.id)
        create_investigation("imei", "356938035643809", "{}", user_id=user_b.id)

        a_counts = aggregate_by_day(days=7, user_id=user_a.id)
        # Only user A's single investigation should be counted in the window.
        assert sum(a_counts.values()) == 1
