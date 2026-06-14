from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.repositories.user_repository import get_by_username, create_user

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
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
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
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

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
