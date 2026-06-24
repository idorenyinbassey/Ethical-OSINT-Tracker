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


def start_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(_rescan_all, "interval", hours=6, args=[app],
                          id="watchlist_rescan", replace_existing=True)
        scheduler.start()
        app.logger.info("APScheduler started — watchlist rescan every 6h")
    except ImportError:
        app.logger.warning("APScheduler not installed — watchlist auto-rescan disabled. Run: pip install apscheduler")
    except Exception as exc:
        app.logger.warning(f"Scheduler failed to start: {exc}")
