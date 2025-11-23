import reflex as rx
from app.components.layout import sidebar, header
from app.components.investigation_tools import tools_tabs


def investigation_page() -> rx.Component:
    return rx.el.div(
        sidebar(active_item="Investigations"),
        rx.el.main(
            header(),
            rx.el.div(
                rx.el.div(
                    rx.el.h1(
                        "Investigation Tools",
                        class_name="text-2xl font-bold text-gray-900 mb-2",
                    ),
                    rx.el.p(
                        "Access powerful OSINT utilities for thorough and ethical data gathering.",
                        class_name="text-gray-500 mb-8",
                    ),
                    tools_tabs(),
                    class_name="max-w-5xl mx-auto",
                ),
                class_name="p-6 lg:p-8 w-full",
            ),
            class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
        ),
        class_name="flex min-h-screen bg-gray-50",
    )