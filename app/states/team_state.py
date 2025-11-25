import reflex as rx
from typing import TypedDict, Optional
import asyncio
from app.states.auth_state import AuthState
from app.repositories.team_repository import (
    list_teams, create_team, delete_team,
    list_team_members, add_team_member, remove_team_member, update_member_role
)
from app.repositories.user_repository import list_users


class TeamItem(TypedDict):
    id: int
    name: str
    description: str
    created_at: str
    owner_user_id: Optional[int]


class MemberItem(TypedDict):
    id: int
    team_id: int
    user_id: int
    role: str
    joined_at: str


class UserItem(TypedDict):
    id: int
    username: str


class TeamState(rx.State):
    # Teams
    teams: list[TeamItem] = []
    selected_team_id: Optional[int] = None
    is_loading_teams: bool = False
    
    # Team creation
    form_team_name: str = ""
    form_team_description: str = ""
    show_create_team_form: bool = False
    is_creating_team: bool = False
    
    # Members
    team_members: list[MemberItem] = []
    available_users: list[UserItem] = []
    is_loading_members: bool = False
    
    # Add member
    form_new_member_user_id: str = ""
    form_new_member_role: str = "member"
    show_add_member_form: bool = False
    is_adding_member: bool = False

    def set_form_team_name(self, value: str):
        self.form_team_name = value

    def set_form_team_description(self, value: str):
        self.form_team_description = value

    def set_form_new_member_user_id(self, value: str):
        self.form_new_member_user_id = value

    def set_form_new_member_role(self, value: str):
        self.form_new_member_role = value
    
    @rx.var
    def user_select_options(self) -> list[dict]:
        """Options for user selection dropdown"""
        return [{"value": str(u['id']), "label": f"{u['id']} - {u['username']}"} for u in self.available_users]

    @rx.event
    def load_teams(self):
        """Load all teams"""
        self.is_loading_teams = True
        yield
        try:
            teams = list_teams()
            self.teams = [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "created_at": str(t.created_at),
                    "owner_user_id": t.owner_user_id,
                }
                for t in teams
            ]
        except Exception:
            self.teams = []
        self.is_loading_teams = False

    @rx.event
    def select_team(self, team_id: int):
        """Select a team and load its members"""
        self.selected_team_id = team_id
        self.load_team_members()

    @rx.event
    def load_team_members(self):
        """Load members of selected team"""
        if not self.selected_team_id:
            return
        
        self.is_loading_members = True
        yield
        try:
            members = list_team_members(self.selected_team_id)
            self.team_members = [
                {
                    "id": m.id,
                    "team_id": m.team_id,
                    "user_id": m.user_id,
                    "role": m.role,
                    "joined_at": str(m.joined_at),
                }
                for m in members
            ]
            # Load available users for adding
            users = list_users()
            self.available_users = [
                {"id": u.id, "username": u.username}
                for u in users
            ]
        except Exception:
            self.team_members = []
            self.available_users = []
        self.is_loading_members = False

    @rx.event
    def show_create_form(self):
        """Show create team form"""
        self.show_create_team_form = True
        self.form_team_name = ""
        self.form_team_description = ""

    @rx.event
    def cancel_create_form(self):
        """Cancel team creation"""
        self.show_create_team_form = False

    @rx.event
    async def create_new_team(self):
        """Create a new team"""
        if not self.form_team_name:
            yield rx.toast.error("Team name is required")
            return
        
        self.is_creating_team = True
        yield
        await asyncio.sleep(0.3)
        
        try:
            create_team(
                name=self.form_team_name,
                description=self.form_team_description,
                owner_user_id=AuthState.current_user_id
            )
            self.show_create_team_form = False
            self.load_teams()
            yield rx.toast.success("Team created successfully")
        except Exception as e:
            yield rx.toast.error(f"Failed to create team: {str(e)}")
        finally:
            self.is_creating_team = False

    @rx.event
    async def delete_team_action(self, team_id: int):
        """Delete a team"""
        try:
            delete_team(team_id)
            if self.selected_team_id == team_id:
                self.selected_team_id = None
                self.team_members = []
            self.load_teams()
            yield rx.toast.success("Team deleted")
        except Exception:
            yield rx.toast.error("Failed to delete team")

    @rx.event
    def open_add_member_form(self):
        """Show add member form"""
        self.show_add_member_form = True
        self.form_new_member_user_id = ""
        self.form_new_member_role = "member"

    @rx.event
    def close_add_member_form(self):
        """Cancel add member"""
        self.show_add_member_form = False

    @rx.event
    async def add_member(self):
        """Add member to selected team"""
        if not self.selected_team_id or not self.form_new_member_user_id:
            yield rx.toast.error("Team and user must be selected")
            return
        
        self.is_adding_member = True
        yield
        await asyncio.sleep(0.3)
        
        try:
            user_id = int(self.form_new_member_user_id)
            add_team_member(
                team_id=self.selected_team_id,
                user_id=user_id,
                role=self.form_new_member_role
            )
            self.show_add_member_form = False
            self.load_team_members()
            yield rx.toast.success("Member added successfully")
        except Exception as e:
            yield rx.toast.error(f"Failed to add member: {str(e)}")
        finally:
            self.is_adding_member = False

    @rx.event
    async def remove_member(self, user_id: int):
        """Remove member from team"""
        if not self.selected_team_id:
            return
        
        try:
            remove_team_member(self.selected_team_id, user_id)
            self.load_team_members()
            yield rx.toast.success("Member removed")
        except Exception:
            yield rx.toast.error("Failed to remove member")

    @rx.event
    async def change_member_role(self, user_id: int, new_role: str):
        """Change member role"""
        if not self.selected_team_id:
            return
        
        try:
            update_member_role(self.selected_team_id, user_id, new_role)
            self.load_team_members()
            yield rx.toast.success("Role updated")
        except Exception:
            yield rx.toast.error("Failed to update role")
