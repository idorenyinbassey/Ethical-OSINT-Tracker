import reflex as rx
from app.components.layout import sidebar, header
from app.components.dashboard_widgets import (
    stat_card,
    activity_feed,
    quick_actions_grid,
    principles_section,
)
from app.components.charts import threat_trends_chart, investigation_metrics_chart
from app.states.dashboard_state import DashboardState
from app.pages.investigation import investigation_page


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
                        "check-circle-2",
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
        ),
        class_name="flex min-h-screen bg-gray-50",
    )


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