from functools import wraps
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from argon2 import PasswordHasher
from app.repositories.user_repository import (
    list_users, get_by_id, update_password, set_admin, set_active, delete_user,
)
from app.utils.audit import log as audit_log

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ph = PasswordHasher()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = list_users()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    new_pw = request.form.get("new_password", "").strip()
    confirm = request.form.get("confirm_password", "").strip()

    if len(new_pw) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin.users"))
    if new_pw != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("admin.users"))

    update_password(user_id, ph.hash(new_pw))
    audit_log("admin.reset_password", entity_type="user", entity_id=user_id,
               detail=f"admin reset password for {user.username}")
    flash(f"Password reset for {user.username}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        flash("You cannot change your own admin status.", "error")
        return redirect(url_for("admin.users"))
    user = get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))
    new_val = not getattr(user, "is_admin", False)
    set_admin(user_id, new_val)
    action = "granted admin" if new_val else "revoked admin"
    audit_log("admin.toggle_admin", entity_type="user", entity_id=user_id,
               detail=f"{action} for {user.username}")
    flash(f"Admin {'granted to' if new_val else 'revoked from'} {user.username}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    if user_id == current_user.id:
        flash("You cannot disable your own account.", "error")
        return redirect(url_for("admin.users"))
    user = get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))
    new_val = not getattr(user, "is_active", True)
    set_active(user_id, new_val)
    audit_log("admin.toggle_active", entity_type="user", entity_id=user_id,
               detail=f"{'enabled' if new_val else 'disabled'} {user.username}")
    flash(f"{user.username} {'enabled' if new_val else 'disabled'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    user = get_by_id(user_id)
    username = user.username if user else str(user_id)
    delete_user(user_id)
    audit_log("admin.delete_user", entity_type="user", entity_id=user_id,
               detail=f"deleted user {username}")
    flash(f"User {username} deleted.", "success")
    return redirect(url_for("admin.users"))
