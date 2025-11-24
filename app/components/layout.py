import reflex as rx
from app.states.dashboard_state import DashboardState
from app.states.notification_state import NotificationState
from app.states.auth_state import AuthState


def sidebar_item(
    label: str, icon_name: str, is_active: bool = False, url: str = "#"
) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(
                icon_name,
                class_name=f"w-5 h-5 {('text-orange-500' if is_active else 'text-gray-400 group-hover:text-orange-500')} transition-colors",
            ),
            rx.el.span(
                label,
                class_name=f"ml-3 text-sm font-medium {('text-gray-900' if is_active else 'text-gray-600 group-hover:text-gray-900')}",
            ),
            class_name="flex items-center",
        ),
        href=url,
        on_click=DashboardState.close_sidebar,
        class_name=f"flex items-center px-4 py-3 rounded-xl transition-all duration-200 group mb-1 {('bg-orange-50' if is_active else 'hover:bg-gray-50')}",
    )


def sidebar(active_item: str = "Dashboard") -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.icon("scan-eye", class_name="w-8 h-8 text-orange-500"),
                rx.el.div(
                    rx.el.h1(
                        "OSINT",
                        class_name="text-xl font-bold text-gray-900 leading-none",
                    ),
                    rx.el.span(
                        "TRACKER",
                        class_name="text-xs font-bold text-orange-500 tracking-widest",
                    ),
                    class_name="ml-2 flex flex-col",
                ),
                class_name="flex items-center",
            ),
            class_name="px-6 py-8",
        ),
        rx.el.nav(
            rx.el.div(
                rx.el.p(
                    "MENU",
                    class_name="px-4 text-xs font-semibold text-gray-400 mb-2 tracking-wider",
                ),
                sidebar_item(
                    "Dashboard",
                    "layout-dashboard",
                    is_active=active_item == "Dashboard",
                    url="/",
                ),
                sidebar_item(
                    "Investigations",
                    "search",
                    is_active=active_item == "Investigations",
                    url="/investigate",
                ),
                sidebar_item(
                    "Threat Map",
                    "globe",
                    is_active=active_item == "Threat Map",
                    url="/threat-map",
                ),
                sidebar_item(
                    "Cases",
                    "folder-open",
                    is_active=active_item == "Cases",
                    url="/cases",
                ),
                class_name="mb-8",
            ),
            rx.el.div(
                rx.el.p(
                    "ANALYTICS",
                    class_name="px-4 text-xs font-semibold text-gray-400 mb-2 tracking-wider",
                ),
                sidebar_item(
                    "Reports",
                    "file-bar-chart",
                    is_active=active_item == "Reports",
                    url="/report",
                ),
                sidebar_item(
                    "Intelligence",
                    "brain-circuit",
                    is_active=active_item == "Intelligence",
                    url="#",
                ),
                class_name="mb-8",
            ),
            rx.el.div(
                rx.el.p(
                    "SETTINGS",
                    class_name="px-4 text-xs font-semibold text-gray-400 mb-2 tracking-wider",
                ),
                sidebar_item(
                    "Team",
                    "users",
                    is_active=active_item == "Team",
                    url="/team",
                ),
                sidebar_item(
                    "Settings",
                    "settings",
                    is_active=active_item == "Settings",
                    url="/settings",
                ),
                class_name="mb-8",
            ),
            class_name="flex-1 px-4 overflow-y-auto",
        ),
        rx.el.div(
            rx.el.div(
                rx.image(
                    src="https://api.dicebear.com/9.x/notionists/svg?seed=Felix",
                    class_name="w-10 h-10 rounded-full bg-gray-100",
                ),
                rx.el.div(
                    rx.el.p(
                        "Agent Smith", class_name="text-sm font-bold text-gray-900"
                    ),
                    rx.el.p("Senior Analyst", class_name="text-xs text-gray-500"),
                    class_name="ml-3",
                ),
                class_name="flex items-center",
            ),
            rx.icon(
                "log-out",
                class_name="w-5 h-5 text-gray-400 hover:text-gray-600 cursor-pointer",
            ),
            class_name="p-4 mx-4 mb-4 bg-white border border-gray-100 rounded-xl flex items-center justify-between shadow-sm",
        ),
        class_name=rx.cond(
            DashboardState.is_sidebar_open,
            "w-72 h-screen bg-white border-r border-gray-100 flex flex-col fixed left-0 top-0 z-50 shadow-2xl transition-transform duration-300 transform translate-x-0",
            "w-72 h-screen bg-white border-r border-gray-100 flex-col fixed left-0 top-0 z-50 hidden lg:flex transition-transform duration-300",
        ),
    )


def notification_item(notification) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.cond(
                notification["type"] == "success",
                rx.icon("circle-check-big", class_name="w-5 h-5 text-green-500"),
                rx.cond(
                    notification["type"] == "error",
                    rx.icon("circle-alert", class_name="w-5 h-5 text-red-500"),
                    rx.icon("info", class_name="w-5 h-5 text-blue-500"),
                ),
            ),
            rx.el.div(
                rx.el.h4(
                    notification["title"],
                    class_name="text-sm font-semibold text-gray-900",
                ),
                rx.el.p(
                    notification["message"],
                    class_name="text-xs text-gray-600 mt-0.5",
                ),
                rx.el.p(
                    notification["timestamp"],
                    class_name="text-xs text-gray-400 mt-1",
                ),
                class_name="ml-3 flex-1",
            ),
            rx.cond(
                ~notification["read"],
                rx.el.button(
                    rx.icon("x", class_name="w-4 h-4"),
                    on_click=lambda: NotificationState.mark_as_read(notification["id"]),
                    class_name="p-1 text-gray-400 hover:text-gray-600 rounded",
                ),
            ),
            class_name="flex items-start",
        ),
        class_name=rx.cond(
            notification["read"],
            "p-4 border-b border-gray-100 bg-gray-50",
            "p-4 border-b border-gray-100 bg-white",
        ),
    )


def notification_drawer() -> rx.Component:
    return rx.cond(
        NotificationState.is_drawer_open,
        rx.el.div(
            rx.el.div(
                on_click=NotificationState.toggle_drawer,
                class_name="fixed inset-0 bg-black/20 z-40",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Notifications",
                        class_name="text-lg font-bold text-gray-900",
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Mark All Read",
                            on_click=NotificationState.mark_all_read,
                            class_name="text-xs text-orange-500 hover:text-orange-600 font-medium",
                        ),
                        rx.el.button(
                            rx.icon("x", class_name="w-5 h-5"),
                            on_click=NotificationState.toggle_drawer,
                            class_name="ml-3 p-1 text-gray-400 hover:text-gray-600 rounded",
                        ),
                        class_name="flex items-center",
                    ),
                    class_name="flex items-center justify-between p-4 border-b border-gray-100",
                ),
                rx.el.div(
                    rx.cond(
                        NotificationState.notifications.length() > 0,
                        rx.foreach(
                            NotificationState.notifications,
                            notification_item,
                        ),
                        rx.el.div(
                            rx.icon("bell-off", class_name="w-12 h-12 text-gray-300 mb-2"),
                            rx.el.p(
                                "No notifications",
                                class_name="text-sm text-gray-500",
                            ),
                            class_name="flex flex-col items-center justify-center py-12",
                        ),
                    ),
                    class_name="overflow-y-auto flex-1",
                ),
                rx.el.div(
                    rx.el.button(
                        "Clear All",
                        on_click=NotificationState.clear_notifications,
                        class_name="w-full py-3 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors",
                    ),
                    class_name="border-t border-gray-100 bg-gray-50",
                ),
                class_name="fixed right-0 top-0 h-screen w-96 bg-white shadow-2xl z-50 flex flex-col",
            ),
            class_name="fixed inset-0 z-40",
        ),
    )


def header() -> rx.Component:
    return rx.el.header(
        notification_drawer(),
        rx.el.div(
            rx.el.button(
                rx.icon("menu", class_name="w-6 h-6 text-gray-700"),
                on_click=DashboardState.toggle_sidebar,
                class_name="lg:hidden p-2 mr-2 hover:bg-gray-100 rounded-lg",
            ),
            rx.el.div(
                rx.icon(
                    "search",
                    class_name="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2",
                ),
                rx.el.input(
                    placeholder="Search investigations, IPs, or domains...",
                    on_change=DashboardState.set_search_query,
                    class_name="w-full pl-10 pr-4 py-2.5 bg-gray-50 border-none rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-orange-100 focus:bg-white transition-all duration-200 outline-none placeholder-gray-400",
                    default_value=DashboardState.search_query,
                ),
                class_name="relative w-full max-w-md hidden md:block",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("bell", class_name="w-5 h-5 text-gray-600"),
                    rx.cond(
                        NotificationState.unread_count > 0,
                        rx.el.div(
                            NotificationState.unread_count,
                            class_name="absolute top-1 right-1 min-w-[18px] h-[18px] bg-orange-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1",
                        ),
                    ),
                    on_click=NotificationState.toggle_drawer,
                    class_name="p-2.5 bg-white rounded-xl border border-gray-100 hover:bg-gray-50 relative transition-colors",
                ),
                rx.menu.root(
                    rx.menu.trigger(
                        rx.el.button(
                            rx.icon("circle_plus", class_name="w-5 h-5 text-gray-600"),
                            class_name="p-2.5 bg-white rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors",
                        ),
                    ),
                    rx.menu.content(
                        rx.menu.item("New Investigation", on_click=rx.redirect("/investigate")),
                        rx.menu.separator(),
                        rx.menu.item("Export Data", on_click=rx.toast.info("Export feature coming soon")),
                        rx.menu.item("Generate Report", on_click=rx.toast.info("Report feature coming soon")),
                        rx.menu.separator(),
                        rx.menu.item(
                            "Logout",
                            on_click=AuthState.logout,
                            color="red",
                        ),
                    ),
                ),
                rx.el.div(
                    rx.el.a(
                        "New Investigation",
                        rx.icon("plus", class_name="w-4 h-4 ml-2"),
                        href="/investigate",
                        class_name="flex items-center px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 transition-colors shadow-lg shadow-gray-200",
                    ),
                    class_name="ml-2",
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="flex justify-between items-center h-20 px-8 border-b border-gray-100 bg-white/80 backdrop-blur-md sticky top-0 z-40",
        ),
        class_name="w-full",
    )