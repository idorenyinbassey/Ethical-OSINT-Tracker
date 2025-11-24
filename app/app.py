import reflex as rx
from app.components.layout import sidebar, header
from app.components.dashboard_widgets import (
    stat_card,
    activity_feed,
    quick_actions_grid,
    principles_section,
    investigation_history,
)
from app.components.charts import threat_trends_chart, investigation_metrics_chart
from app.states.dashboard_state import DashboardState
from app.pages.investigation import investigation_page
from app.pages.auth import auth_page
from app.pages.register import register_page
from app.pages.settings import settings_page
from app.pages.cases import cases_page
from app.pages.threat_map import threat_map_page
from app.pages.report import report_page
from app.pages.team import team_page
from app.db import init_db


def index() -> rx.Component:
    return rx.el.div(
        sidebar(active_item="Dashboard"),
        rx.el.main(
            header(),
            rx.el.div(
                rx.el.div(
                    stat_card(
                        "Active Investigations",
                        DashboardState.active_investigations,
                        "microscope",
                        "+12%",
                        True,
                    ),
                    stat_card(
                        "Threats Identified",
                        DashboardState.threats_identified,
                        "shield-alert",
                        "+8%",
                        True,
                    ),
                    stat_card(
                        "Cases Closed",
                        DashboardState.cases_closed,
                        "circle-check-big",
                        "+24%",
                        True,
                    ),
                    class_name="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8",
                ),
                rx.el.div(
                    rx.el.div(
                        quick_actions_grid(),
                        rx.el.div(
                            threat_trends_chart(),
                            investigation_metrics_chart(),
                            class_name="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8",
                        ),
                        investigation_history(),
                        principles_section(),
                        class_name="col-span-12 lg:col-span-8",
                    ),
                    rx.el.div(
                        activity_feed(), class_name="col-span-12 lg:col-span-4 h-full"
                    ),
                    class_name="grid grid-cols-12 gap-6",
                ),
                class_name="p-6 lg:p-8 max-w-[1600px] mx-auto",
            ),
            class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
            on_mount=DashboardState.refresh_dashboard,
        ),
        class_name="flex min-h-screen bg-gray-50",
    )


init_db()

app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        )
    ],
)
app.add_page(index, route="/")
app.add_page(investigation_page, route="/investigate")
app.add_page(auth_page, route="/login")
app.add_page(register_page, route="/register")
app.add_page(settings_page, route="/settings")
app.add_page(cases_page, route="/cases")
app.add_page(threat_map_page, route="/threat-map")
app.add_page(report_page, route="/report")
app.add_page(team_page, route="/team")