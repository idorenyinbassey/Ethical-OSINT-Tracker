"""Background scheduler — auto-rescan watchlist targets every 6 hours."""
import hashlib
import json
import datetime


def _rescan_all(app):
    with app.app_context():
        try:
            from app.repositories.watchlist_repository import list_all_targets, update_checked, set_alert
            from app.repositories.investigation_repository import find_or_update_recent

            targets = list_all_targets()
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=6)

            for target in targets:
                if target.last_checked and target.last_checked > cutoff:
                    continue  # checked recently enough

                result = {}
                try:
                    if target.kind == "ip":
                        from app.services import ip_client
                        result = ip_client.fetch_ip(target.query) or {}
                    elif target.kind == "domain":
                        from app.services import rdap_client
                        result = rdap_client.fetch_domain(target.query) or {}
                    elif target.kind == "email":
                        from app.services import hibp_client
                        breaches = hibp_client.check_breaches(target.query)
                        result = {"breaches": breaches}
                    elif target.kind == "social":
                        from app.services import social_client
                        result = social_client.search_username(target.query) or {}
                    elif target.kind == "crypto":
                        from app.services import crypto_client
                        result = crypto_client.lookup(target.query) or {}
                    elif target.kind == "phone":
                        from app.services import numverify_client
                        result = numverify_client.fetch_phone(target.query) or {}
                except Exception as exc:
                    result = {"error": str(exc)}

                result_json = json.dumps(result, default=str)
                new_hash = hashlib.sha256(result_json.encode()).hexdigest()[:16]
                changed = bool(target.last_result_hash) and new_hash != target.last_result_hash

                update_checked(target.id, new_hash)

                if changed:
                    set_alert(target.id, f"Data changed at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
                    # Log a new investigation record so the change is traceable
                    find_or_update_recent(
                        kind=target.kind, query=target.query,
                        result_json=result_json, user_id=target.user_id,
                        case_id=target.case_id, confidence="CONFIRMED",
                    )
        except Exception:
            pass  # scheduler jobs must never crash the process


def _purge_retention(app):
    """Delete investigations older than the configured RETENTION_DAYS (Issue #15)."""
    with app.app_context():
        try:
            from app.config import Config
            from app.repositories.investigation_repository import purge_old_investigations
            deleted = purge_old_investigations(Config.RETENTION_DAYS)
            if deleted:
                app.logger.info(
                    "Data retention: purged %d investigations older than %d days",
                    deleted, Config.RETENTION_DAYS,
                )
        except Exception:
            pass  # scheduler jobs must never crash the process


def start_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        # Pin to UTC so the scheduler does not depend on resolving the host's
        # local timezone via the IANA tz database, which is often missing on
        # minimal systems (e.g. Termux/Android — "No time zone found with key ...").
        scheduler = BackgroundScheduler(daemon=True, timezone=datetime.timezone.utc)
        scheduler.add_job(_rescan_all, "interval", hours=6, args=[app],
                          id="watchlist_rescan", replace_existing=True)
        # Enforce the PII data-retention policy once a day.
        scheduler.add_job(_purge_retention, "interval", hours=24, args=[app],
                          id="retention_purge", replace_existing=True)
        scheduler.start()
        # Run an initial purge so retention takes effect immediately on boot.
        _purge_retention(app)
        app.logger.info("APScheduler started — watchlist rescan every 6h, retention purge daily")
    except ImportError:
        app.logger.warning("APScheduler not installed — watchlist auto-rescan disabled. Run: pip install apscheduler")
    except Exception as exc:
        app.logger.warning(f"Scheduler failed to start: {exc}")
