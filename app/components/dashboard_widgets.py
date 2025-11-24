import reflex as rx
from app.states.dashboard_state import DashboardState


def stat_card(
    title: str, value: int, icon_name: str, trend: str, trend_up: bool
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon_name, class_name="w-6 h-6 text-orange-500"),
                class_name="p-3 bg-orange-50 rounded-xl mb-4 w-fit",
            ),
            rx.el.div(
                rx.el.h3(title, class_name="text-sm font-medium text-gray-500 mb-1"),
                rx.el.p(value, class_name="text-3xl font-bold text-gray-900"),
            ),
        ),
        rx.el.div(
            rx.icon(
                rx.cond(trend_up, "trending-up", "trending-down"),
                class_name=f"w-4 h-4 mr-1 {rx.cond(trend_up, 'text-green-500', 'text-red-500')}",
            ),
            rx.el.span(
                trend,
                class_name=f"text-sm font-medium {rx.cond(trend_up, 'text-green-500', 'text-red-500')}",
            ),
            rx.el.span(" vs last week", class_name="text-sm text-gray-400 ml-1"),
            class_name="flex items-center mt-4 pt-4 border-t border-gray-50",
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-300 flex flex-col justify-between",
    )


def activity_item(activity: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                class_name="w-2 h-2 rounded-full bg-orange-500 mt-2 mr-3 flex-shrink-0"
            ),
            rx.el.div(
                rx.el.p(
                    activity["title"], class_name="text-sm font-medium text-gray-800"
                ),
                rx.el.div(
                    rx.el.span(
                        activity["type"],
                        class_name="text-xs uppercase tracking-wider text-gray-500 font-semibold mr-2",
                    ),
                    rx.el.span("•", class_name="text-gray-300 mx-1"),
                    rx.el.span(
                        activity["timestamp"], class_name="text-xs text-gray-400"
                    ),
                    class_name="flex items-center mt-1",
                ),
            ),
        ),
        rx.el.div(
            rx.el.span(
                activity["status"],
                class_name=rx.cond(
                    activity["status"] == "Critical",
                    "bg-red-100 text-red-700",
                    rx.cond(
                        activity["status"] == "High Risk",
                        "bg-orange-100 text-orange-700",
                        "bg-gray-100 text-gray-600",
                    ),
                )
                + " text-xs px-2 py-1 rounded-md font-medium",
            )
        ),
        class_name="flex items-start justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors duration-200",
    )


def activity_feed() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                "Recent Activity", class_name="text-lg font-semibold text-gray-800"
            ),
            rx.el.button(
                "View All",
                class_name="text-sm text-orange-600 hover:text-orange-700 font-medium",
            ),
            class_name="flex justify-between items-center mb-4 px-2",
        ),
        rx.el.div(
            rx.foreach(DashboardState.activities, activity_item),
            class_name="flex flex-col gap-1",
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-full",
    )


def quick_action_btn(label: str, icon_name: str, color_class: str, on_click=None) -> rx.Component:
    """Reusable quick action button with optional click handler."""
    return rx.el.button(
        rx.el.div(
            rx.icon(icon_name, class_name="w-6 h-6 text-white"),
            class_name=f"w-12 h-12 rounded-xl {color_class} flex items-center justify-center mb-3 shadow-sm group-hover:scale-110 transition-transform duration-200",
        ),
        rx.el.span(
            label,
            class_name="text-sm font-medium text-gray-700 group-hover:text-gray-900",
        ),
        on_click=on_click,
        class_name="group flex flex-col items-center justify-center p-4 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 aspect-square",
    )


def quick_actions_grid() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Quick Actions", class_name="text-lg font-semibold text-gray-800 mb-4 px-2"
        ),
        rx.el.div(
            quick_action_btn("Investigate", "search", "bg-orange-500", rx.redirect("/investigate")),
            quick_action_btn("New Case", "folder-plus", "bg-gray-700", rx.redirect("/cases")),
            quick_action_btn("Run Analysis", "activity", "bg-blue-500", rx.redirect("/report")),
            quick_action_btn("Report", "file-text", "bg-emerald-500", rx.redirect("/report")),
            class_name="grid grid-cols-2 md:grid-cols-4 gap-4",
        ),
        class_name="w-full mb-8",
    )


def principle_item(title: str, desc: str, icon: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="w-5 h-5 text-orange-500 mt-1 flex-shrink-0"),
        rx.el.div(
            rx.el.h4(title, class_name="text-sm font-bold text-gray-800"),
            rx.el.p(desc, class_name="text-xs text-gray-500 mt-1 leading-relaxed"),
            class_name="ml-3",
        ),
        class_name="flex items-start p-3 bg-gray-50 rounded-xl border border-gray-100",
    )


def principles_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                "OSINT4GOOD Principles",
                class_name="text-lg font-semibold text-gray-800",
            ),
            rx.icon("shield-check", class_name="w-5 h-5 text-gray-400"),
            class_name="flex justify-between items-center mb-4",
        ),
        rx.el.div(
            principle_item(
                "Legal Compliance",
                "Adhere strictly to all applicable laws and regulations.",
                "scale",
            ),
            principle_item(
                "Privacy Protection",
                "Respect privacy rights and minimize data collection.",
                "lock",
            ),
            principle_item(
                "Accuracy & Verification",
                "Verify all information before reporting or acting.",
                "check_check",
            ),
            principle_item(
                "Responsible Disclosure",
                "Report vulnerabilities through proper channels.",
                "flag_triangle_right",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
    )


def investigation_history_item(inv: dict) -> rx.Component:
    icon_map = {
        "domain": "globe",
        "ip": "map-pin",
        "email": "mail",
        "social": "users",
        "phone": "phone",
        "image": "scan-face",
        "imei": "smartphone",
    }
    color_map = {
        "domain": "text-blue-500",
        "ip": "text-green-500",
        "email": "text-purple-500",
        "social": "text-pink-500",
        "phone": "text-orange-500",
        "image": "text-red-500",
        "imei": "text-teal-500",
    }
    return rx.el.div(
        rx.el.div(
            rx.icon(
                icon_map.get(inv["kind"], "search"),
                class_name=f"w-4 h-4 {color_map.get(inv['kind'], 'text-gray-500')}",
            ),
            rx.el.div(
                rx.el.span(
                    inv["kind"].upper(),
                    class_name="text-xs font-bold text-gray-500 uppercase tracking-wider",
                ),
                rx.el.p(
                    inv["query"], class_name="text-sm text-gray-800 truncate max-w-xs"
                ),
                class_name="ml-2",
            ),
            class_name="flex items-start",
        ),
        rx.el.span(inv["created_at"], class_name="text-xs text-gray-400"),
        class_name="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors",
    )


def investigation_history() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                "Recent Investigations",
                class_name="text-lg font-semibold text-gray-800",
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="w-4 h-4"),
                on_click=DashboardState.load_recent_investigations,
                class_name="text-sm text-orange-600 hover:text-orange-700 font-medium p-2 hover:bg-orange-50 rounded-lg transition-colors",
            ),
            class_name="flex justify-between items-center mb-4 px-2",
        ),
        rx.cond(
            DashboardState.recent_investigations.length() > 0,
            rx.el.div(
                rx.foreach(
                    DashboardState.recent_investigations, investigation_history_item
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.icon("inbox", class_name="w-8 h-8 text-gray-300 mb-2"),
                rx.el.p(
                    "No investigations yet",
                    class_name="text-sm text-gray-500 font-medium",
                ),
                rx.el.p(
                    "Start an investigation to see history here",
                    class_name="text-xs text-gray-400",
                ),
                class_name="flex flex-col items-center justify-center py-12 text-center",
            ),
        ),
        class_name="bg-white p-6 rounded-2xl shadow-sm border border-gray-100",
        on_mount=DashboardState.load_recent_investigations,
    )