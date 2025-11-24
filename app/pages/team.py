import reflex as rx
from app.components.layout import sidebar, header
from app.states.auth_state import AuthState
from app.states.team_state import TeamState


def role_badge(role: str) -> rx.Component:
    """Colored badge for team role"""
    colors = {
        "owner": "bg-purple-100 text-purple-700",
        "admin": "bg-blue-100 text-blue-700",
        "analyst": "bg-green-100 text-green-700",
        "member": "bg-gray-100 text-gray-700",
    }
    return rx.el.span(
        role.capitalize(),
        class_name=f"px-2 py-1 rounded text-xs font-medium {colors.get(role, 'bg-gray-100 text-gray-700')}"
    )


def team_card(team) -> rx.Component:
    """Card for each team"""
    return rx.el.div(
        rx.el.div(
            rx.el.h3(team["name"], class_name="text-lg font-semibold text-gray-900 mb-2"),
            rx.el.p(
                rx.cond(team["description"], team["description"], "No description"),
                class_name="text-sm text-gray-600 mb-3"
            ),
            rx.el.div(
                rx.icon("calendar", class_name="w-4 h-4 text-gray-400 mr-1"),
                rx.el.span(
                    f"Created {team['created_at'][:10]}",
                    class_name="text-xs text-gray-500"
                ),
                class_name="flex items-center mb-3"
            ),
            rx.el.div(
                rx.el.button(
                    "View Members",
                    on_click=lambda: TeamState.select_team(team["id"]),
                    class_name="px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-xs font-medium mr-2"
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="w-4 h-4"),
                    on_click=lambda: TeamState.delete_team_action(team["id"]),
                    class_name="px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs"
                ),
                class_name="flex items-center"
            ),
        ),
        class_name="p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md transition-shadow"
    )


def member_row(member) -> rx.Component:
    """Row for team member"""
    return rx.el.div(
        rx.el.div(
            rx.icon("user", class_name="w-5 h-5 text-gray-400 mr-3"),
            rx.el.div(
                rx.el.p(f"User ID: {member['user_id']}", class_name="text-sm font-medium text-gray-900"),
                rx.el.p(f"Joined {member['joined_at'][:10]}", class_name="text-xs text-gray-500"),
                class_name="flex-1"
            ),
            class_name="flex items-center flex-1"
        ),
        rx.el.div(
            role_badge(member["role"]),
            rx.el.select(
                ["member", "analyst", "admin", "owner"],
                value=member["role"],
                on_change=lambda val: TeamState.change_member_role(member["user_id"], val),
                class_name="ml-3 px-2 py-1 text-xs border border-gray-200 rounded"
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="w-4 h-4"),
                on_click=lambda: TeamState.remove_member(member["user_id"]),
                class_name="ml-3 p-1.5 text-red-600 hover:bg-red-50 rounded"
            ),
            class_name="flex items-center"
        ),
        class_name="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
    )


def create_team_form() -> rx.Component:
    """Modal for creating new team"""
    return rx.cond(
        TeamState.show_create_team_form,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3("Create New Team", class_name="text-lg font-bold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", class_name="w-5 h-5"),
                        on_click=TeamState.cancel_create_form,
                        class_name="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
                    ),
                    class_name="flex items-center justify-between mb-6"
                ),
                rx.el.div(
                    rx.el.label("Team Name", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.input(
                        placeholder="Enter team name",
                        on_change=TeamState.set_form_team_name,
                        value=TeamState.form_team_name,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                    ),
                    class_name="mb-4"
                ),
                rx.el.div(
                    rx.el.label("Description", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.textarea(
                        placeholder="Team description",
                        on_change=TeamState.set_form_team_description,
                        value=TeamState.form_team_description,
                        rows="3",
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none resize-none"
                    ),
                    class_name="mb-6"
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancel",
                        on_click=TeamState.cancel_create_form,
                        class_name="px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-200 transition-colors"
                    ),
                    rx.el.button(
                        rx.cond(TeamState.is_creating_team, rx.spinner(size="1"), "Create Team"),
                        on_click=TeamState.create_new_team,
                        disabled=TeamState.is_creating_team,
                        class_name="px-4 py-2.5 bg-orange-500 text-white text-sm font-medium rounded-xl hover:bg-orange-600 transition-colors ml-3"
                    ),
                    class_name="flex justify-end"
                ),
                class_name="bg-white p-6 rounded-2xl border border-gray-200 max-w-lg w-full"
            ),
            class_name="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        )
    )


def add_member_form() -> rx.Component:
    """Modal for adding member to team"""
    return rx.cond(
        TeamState.show_add_member_form,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3("Add Team Member", class_name="text-lg font-bold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", class_name="w-5 h-5"),
                        on_click=TeamState.close_add_member_form,
                        class_name="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
                    ),
                    class_name="flex items-center justify-between mb-6"
                ),
                rx.el.div(
                    rx.el.label("User", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.select(
                        rx.foreach(
                            TeamState.user_select_options,
                            lambda opt: rx.el.option(opt["label"], value=opt["value"])
                        ),
                        on_change=TeamState.set_form_new_member_user_id,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                    ),
                    class_name="mb-4"
                ),
                rx.el.div(
                    rx.el.label("Role", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.select(
                        ["member", "analyst", "admin"],
                        value=TeamState.form_new_member_role,
                        on_change=TeamState.set_form_new_member_role,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                    ),
                    class_name="mb-6"
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancel",
                        on_click=TeamState.close_add_member_form,
                        class_name="px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-200 transition-colors"
                    ),
                    rx.el.button(
                        rx.cond(TeamState.is_adding_member, rx.spinner(size="1"), "Add Member"),
                        on_click=TeamState.add_member,
                        disabled=TeamState.is_adding_member,
                        class_name="px-4 py-2.5 bg-orange-500 text-white text-sm font-medium rounded-xl hover:bg-orange-600 transition-colors ml-3"
                    ),
                    class_name="flex justify-end"
                ),
                class_name="bg-white p-6 rounded-2xl border border-gray-200 max-w-lg w-full"
            ),
            class_name="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        )
    )


def team_page() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            sidebar(active_item="Team"),
            rx.el.main(
                header(),
                create_team_form(),
                add_member_form(),
                rx.el.div(
                    # Header
                    rx.el.div(
                        rx.el.h1("Teams", class_name="text-2xl font-bold text-gray-900 mb-2"),
                        rx.el.p("Collaborate on investigations with your team", class_name="text-gray-600"),
                        class_name="mb-6"
                    ),
                    
                    # Create team button
                    rx.el.div(
                        rx.el.button(
                            rx.icon("plus", class_name="w-4 h-4 mr-2"),
                            "New Team",
                            on_click=TeamState.show_create_form,
                            class_name="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                        ),
                        class_name="mb-6"
                    ),
                    
                    # Teams grid
                    rx.el.div(
                        rx.el.h2("My Teams", class_name="text-xl font-bold text-gray-900 mb-4"),
                        rx.cond(
                            TeamState.teams.length() > 0,
                            rx.el.div(
                                rx.foreach(TeamState.teams, team_card),
                                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8"
                            ),
                            rx.el.div(
                                rx.icon("users", class_name="w-12 h-12 text-gray-300 mb-2"),
                                rx.el.p("No teams yet", class_name="text-sm text-gray-500"),
                                rx.el.button(
                                    "Create your first team",
                                    on_click=TeamState.show_create_form,
                                    class_name="mt-3 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm rounded-lg"
                                ),
                                class_name="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 mb-8"
                            )
                        ),
                    ),
                    
                    # Selected team members
                    rx.cond(
                        TeamState.selected_team_id,
                        rx.el.div(
                            rx.el.div(
                                rx.el.h2("Team Members", class_name="text-xl font-bold text-gray-900"),
                                rx.el.button(
                                    rx.icon("user-plus", class_name="w-4 h-4 mr-2"),
                                    "Add Member",
                                    on_click=TeamState.open_add_member_form,
                                    class_name="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                                ),
                                class_name="flex items-center justify-between mb-4"
                            ),
                            rx.cond(
                                TeamState.team_members.length() > 0,
                                rx.el.div(
                                    rx.foreach(TeamState.team_members, member_row),
                                    class_name="space-y-2"
                                ),
                                rx.el.div(
                                    rx.el.p("No members in this team", class_name="text-sm text-gray-500"),
                                    class_name="py-8 text-center bg-gray-50 rounded-xl"
                                )
                            ),
                        )
                    ),
                    
                    on_mount=TeamState.load_teams,
                    class_name="p-6 lg:p-8 max-w-[1600px] mx-auto"
                ),
                class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']"
            ),
            class_name="flex min-h-screen bg-gray-50"
        ),
        rx.el.div(
            rx.el.p("Login required", class_name="text-sm"),
            class_name="p-6"
        )
    )
