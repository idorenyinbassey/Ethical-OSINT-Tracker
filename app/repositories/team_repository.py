from typing import List
from sqlmodel import select
from app.models.team import Team, TeamMember
from app.repositories.base import session_scope


def list_teams() -> List[Team]:
    """Get all teams"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(Team).order_by(Team.created_at.desc())
        teams = list(session.exec(stmt))
        for team in teams:
            session.expunge(team)
        return teams


def get_team(team_id: int) -> Team | None:
    """Get team by ID"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(Team).where(Team.id == team_id)
        team = session.exec(stmt).first()
        if team:
            session.expunge(team)
        return team


def create_team(name: str, description: str, owner_user_id: int | None) -> Team:
    """Create a new team"""
    with session_scope(expire_on_commit=False) as session:
        team = Team(name=name, description=description, owner_user_id=owner_user_id)
        session.add(team)
        session.flush()
        session.refresh(team)
        session.expunge(team)
        return team


def delete_team(team_id: int) -> bool:
    """Delete team and all members"""
    with session_scope() as session:
        # Delete members first
        stmt_members = select(TeamMember).where(TeamMember.team_id == team_id)
        members = session.exec(stmt_members).all()
        for member in members:
            session.delete(member)
        
        # Delete team
        stmt_team = select(Team).where(Team.id == team_id)
        team = session.exec(stmt_team).first()
        if team:
            session.delete(team)
            return True
        return False


def list_teams_for_user(user_id: int) -> List[Team]:
    """Teams `user_id` is a member of (any role)."""
    with session_scope(expire_on_commit=False) as session:
        team_ids = [
            m.team_id for m in session.exec(
                select(TeamMember).where(TeamMember.user_id == user_id)
            ).all()
        ]
        if not team_ids:
            return []
        stmt = select(Team).where(Team.id.in_(team_ids)).order_by(Team.created_at.desc())
        teams = list(session.exec(stmt))
        for team in teams:
            session.expunge(team)
        return teams


def get_membership(team_id: int, user_id: int) -> TeamMember | None:
    """A user's membership row for a team, or None if they aren't a member."""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        member = session.exec(stmt).first()
        if member:
            session.expunge(member)
        return member


def count_owners(team_id: int) -> int:
    """Number of members with role 'owner' — used to block removing/demoting
    the last owner of a team."""
    with session_scope() as session:
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.role == "owner",
        )
        return len(session.exec(stmt).all())


def list_team_members(team_id: int) -> List[TeamMember]:
    """Get all members of a team"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(TeamMember).where(TeamMember.team_id == team_id)
        members = list(session.exec(stmt))
        for member in members:
            session.expunge(member)
        return members


def add_team_member(team_id: int, user_id: int, role: str = "member") -> TeamMember:
    """Add a member to team"""
    with session_scope(expire_on_commit=False) as session:
        member = TeamMember(team_id=team_id, user_id=user_id, role=role)
        session.add(member)
        session.flush()
        session.refresh(member)
        session.expunge(member)
        return member


def remove_team_member(team_id: int, user_id: int) -> bool:
    """Remove a member from team"""
    with session_scope() as session:
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
        member = session.exec(stmt).first()
        if member:
            session.delete(member)
            return True
        return False


def update_member_role(team_id: int, user_id: int, new_role: str) -> bool:
    """Update team member role"""
    with session_scope() as session:
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
        member = session.exec(stmt).first()
        if member:
            member.role = new_role
            session.add(member)
            return True
        return False
