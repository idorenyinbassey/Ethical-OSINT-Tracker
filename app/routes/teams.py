"""Team management UI.

app/models/team.py (Team/TeamMember) and app/repositories/team_repository.py
already had full CRUD implemented — this file is what was missing:
routes and templates that actually expose it. Modeled directly on
app/routes/admin.py's user-management pattern (inline "create new"
disclosure, one route per mutation, audit_log after every mutation,
CSRF + confirm() on destructive actions).
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.repositories.team_repository import (
    list_teams_for_user, get_team, create_team, delete_team,
    list_team_members, add_team_member, remove_team_member,
    update_member_role, get_membership, count_owners,
)
from app.repositories.user_repository import get_by_username, get_by_id
from app.utils.decorators import team_member_required, team_role_required
from app.utils.audit import log as audit_log

teams_bp = Blueprint("teams", __name__, url_prefix="/teams")

VALID_ROLES = {"owner", "admin", "analyst", "member"}


@teams_bp.route("/")
@login_required
def index():
    teams = list_teams_for_user(current_user.id)
    member_counts = {t.id: len(list_team_members(t.id)) for t in teams}
    return render_template("teams/index.html", teams=teams, member_counts=member_counts)


@teams_bp.route("/create", methods=["POST"])
@login_required
def create():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if len(name) < 2:
        flash("Team name must be at least 2 characters.", "error")
        return redirect(url_for("teams.index"))

    team = create_team(name, description, owner_user_id=current_user.id)
    add_team_member(team.id, current_user.id, role="owner")
    audit_log("team.created", entity_type="team", entity_id=team.id, detail=name)
    flash(f"Team '{name}' created.", "success")
    return redirect(url_for("teams.detail", team_id=team.id))


@teams_bp.route("/<int:team_id>")
@login_required
@team_member_required
def detail(team_id):
    team = get_team(team_id)
    if not team:
        abort(404)
    members = list_team_members(team_id)
    member_rows = []
    for m in members:
        u = get_by_id(m.user_id)
        member_rows.append({"member": m, "username": u.username if u else f"user #{m.user_id}"})
    my_role = get_membership(team_id, current_user.id).role
    return render_template("teams/detail.html", team=team, member_rows=member_rows, my_role=my_role,
                           owner_count=count_owners(team_id))


@teams_bp.route("/<int:team_id>/members/add", methods=["POST"])
@login_required
@team_role_required("owner", "admin")
def add_member(team_id):
    username = request.form.get("username", "").strip()
    role = request.form.get("role", "member")
    if role not in VALID_ROLES:
        flash("Invalid role.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))

    user = get_by_username(username)
    if not user:
        flash(f"No user named '{username}'.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))
    if get_membership(team_id, user.id):
        flash(f"{username} is already a member.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))

    add_team_member(team_id, user.id, role=role)
    audit_log("team.member_added", entity_type="team", entity_id=team_id,
               detail=f"{username} as {role}")
    flash(f"{username} added as {role}.", "success")
    return redirect(url_for("teams.detail", team_id=team_id))


@teams_bp.route("/<int:team_id>/members/<int:user_id>/role", methods=["POST"])
@login_required
@team_role_required("owner", "admin")
def change_role(team_id, user_id):
    new_role = request.form.get("role", "")
    if new_role not in VALID_ROLES:
        flash("Invalid role.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))

    target = get_membership(team_id, user_id)
    if not target:
        flash("That user is not a member of this team.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))
    if target.role == "owner" and new_role != "owner" and count_owners(team_id) <= 1:
        flash("Cannot demote the last owner of a team.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))

    update_member_role(team_id, user_id, new_role)
    audit_log("team.role_changed", entity_type="team", entity_id=team_id,
               detail=f"user {user_id} -> {new_role}")
    flash("Role updated.", "success")
    return redirect(url_for("teams.detail", team_id=team_id))


@teams_bp.route("/<int:team_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
@team_role_required("owner", "admin")
def remove_member(team_id, user_id):
    target = get_membership(team_id, user_id)
    if not target:
        flash("That user is not a member of this team.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))
    if target.role == "owner" and count_owners(team_id) <= 1:
        flash("Cannot remove the last owner of a team.", "error")
        return redirect(url_for("teams.detail", team_id=team_id))

    remove_team_member(team_id, user_id)
    audit_log("team.member_removed", entity_type="team", entity_id=team_id,
               detail=f"user {user_id}")
    flash("Member removed.", "success")
    return redirect(url_for("teams.detail", team_id=team_id))


@teams_bp.route("/<int:team_id>/delete", methods=["POST"])
@login_required
@team_role_required("owner")
def delete(team_id):
    team = get_team(team_id)
    if not team:
        abort(404)
    name = team.name
    delete_team(team_id)
    audit_log("team.deleted", entity_type="team", entity_id=team_id, detail=name)
    flash(f"Team '{name}' deleted.", "success")
    return redirect(url_for("teams.index"))
