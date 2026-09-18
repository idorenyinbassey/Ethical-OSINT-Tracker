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


def _refresh_tac_database(app):
    """Keep the offline IMEI/TAC database (app.services.tac_lookup) from
    going stale. Safe to run repeatedly — refresh_tac_database() rate-limits
    itself and never touches the network more than needed."""
    with app.app_context():
        try:
            from app.services.tac_lookup import refresh_tac_database
            if refresh_tac_database():
                app.logger.info("TAC database refreshed from github.com/MoazEb/tac-database")
        except Exception:
            pass  # scheduler jobs must never crash the process


def _run_scraper_canaries(app):
    """Catch a scraper break (site markup changed underneath a parser)
    within a day instead of via a bug report — see app.utils.scraper_health
    for what's checked and why. A canary failure is reported via the
    configured Notifications webhook, not just a log line, since a
    silently-broken scraper (like the AHMIA anti-bot token issue) can
    otherwise go unnoticed for a long time."""
    with app.app_context():
        try:
            from app.utils.scraper_health import check_and_notify
            check_and_notify()
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
        # Keep the offline TAC database fresh: once ASAP on boot (run via the
        # scheduler, not called directly, since it's a ~12MB network fetch
        # that shouldn't block app startup), then weekly for long-running
        # processes. refresh_tac_database() itself rate-limits to once/day
        # regardless of how often the app restarts.
        scheduler.add_job(_refresh_tac_database, args=[app],
                          id="tac_database_refresh_boot", replace_existing=True)
        scheduler.add_job(_refresh_tac_database, "interval", days=7, args=[app],
                          id="tac_database_refresh_weekly", replace_existing=True)
        # Scraper canaries daily — not urgent enough to also run at boot
        # (unlike the TAC refresh, this makes several live outbound
        # requests purely to check freshness, not to serve a user).
        scheduler.add_job(_run_scraper_canaries, "interval", hours=24, args=[app],
                          id="scraper_canaries", replace_existing=True)
        scheduler.start()
        # Run an initial purge so retention takes effect immediately on boot.
        _purge_retention(app)
        app.logger.info("APScheduler started — watchlist rescan every 6h, retention purge daily, TAC database refresh weekly, scraper canaries daily")
    except ImportError:
        app.logger.warning("APScheduler not installed — watchlist auto-rescan disabled. Run: pip install apscheduler")
    except Exception as exc:
        app.logger.warning(f"Scheduler failed to start: {exc}")
