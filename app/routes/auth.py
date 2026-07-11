from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.repositories.user_repository import get_by_username, create_user
from app.utils.rate_limiter import check_rate_limit
from app.config import Config

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        # Rate limit login attempts per IP: 10 attempts per 60 seconds
        ip_address = request.remote_addr or "unknown"
        allowed, remaining = check_rate_limit(
            key=f"login:{ip_address}",
            max_requests=10,
            window_seconds=60
        )
        if not allowed:
            flash(
                f"Too many login attempts. Please try again in a moment.",
                "error"
            )
            return render_template("auth/login.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_by_username(username)
        if not user:
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        try:
            ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        login_user(user)
        try:
            from app.utils.audit import log as audit_log
            audit_log("login", detail=f"user {username}")
        except Exception:
            pass
        next_page = request.args.get("next", "")
        # Only allow relative redirects to prevent open-redirect attacks
        parsed = urlparse(next_page)
        if parsed.scheme or parsed.netloc:
            next_page = ""
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        # Check if registration is enabled
        if not Config.REGISTRATION_ENABLED:
            flash(
                "Registration is currently disabled. Please contact an administrator.",
                "error"
            )
            return render_template("auth/register.html"), 403

        # Rate limit registration per IP: 3 registrations per hour
        ip_address = request.remote_addr or "unknown"
        allowed, remaining = check_rate_limit(
            key=f"register:{ip_address}",
            max_requests=3,
            window_seconds=3600
        )
        if not allowed:
            flash(
                "Too many registration attempts. Please try again later.",
                "error"
            )
            return render_template("auth/register.html"), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        if get_by_username(username):
            flash("Username already taken.", "error")
            return render_template("auth/register.html")

        password_hash = ph.hash(password)
        user = create_user(username, password_hash)
        login_user(user)
        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard.index"))

    if not Config.REGISTRATION_ENABLED:
        flash(
            "Registration is currently disabled. Please contact an administrator.",
            "error"
        )

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
