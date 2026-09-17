"""Background scheduler — auto-rescan watchlist targets every 6 hours."""
import datetime


def _rescan_all(app):
    with app.app_context():
        try:
            from app.repositories.watchlist_repository import list_all_targets
            from app.services.watchlist_scan_service import fetch_target_data, finalize_scan

            targets = list_all_targets()
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=6)

            for target in targets:
                if target.last_checked and target.last_checked > cutoff:
                    continue  # checked recently enough

                # Fetch, then hash-diff/persist/alert/notify — shared with
                # the API's rescan endpoint (app/routes/api_v1.py) so both
                # automatic triggers behave identically.
                result = fetch_target_data(target)
                finalize_scan(target, result)
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
