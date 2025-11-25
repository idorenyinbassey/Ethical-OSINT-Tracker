import reflex as rx
from app.components.layout import sidebar, header
from app.components.investigation_tools import tools_tabs
from app.states.auth_state import AuthState
from app.states.investigation_state import InvestigationState


def export_actions() -> rx.Component:
    """Export and generate actions for investigations"""
    return rx.el.div(
        rx.el.div(
            rx.el.h3("Export Data", class_name="text-sm font-semibold text-gray-800 mb-2"),
            rx.el.div(
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_exporting,
                        rx.spinner(size="1"),
                        rx.el.div(
                            rx.icon("download", class_name="w-4 h-4"),
                            "Export JSON",
                            class_name="flex items-center gap-2"
                        )
                    ),
                    on_click=lambda: InvestigationState.export_investigations("json"),
                    disabled=InvestigationState.is_exporting,
                    class_name="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
                ),
                rx.el.button(
                    rx.cond(
                        InvestigationState.is_exporting,
                        rx.spinner(size="1"),
                        rx.el.div(
                            rx.icon("download", class_name="w-4 h-4"),
                            "Export CSV",
                            class_name="flex items-center gap-2"
                        )
                    ),
                    on_click=lambda: InvestigationState.export_investigations("csv"),
                    disabled=InvestigationState.is_exporting,
                    class_name="px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
                ),
                class_name="flex gap-2"
            ),
            rx.cond(
                InvestigationState.export_result,
                rx.el.div(
                    rx.el.textarea(
                        value=InvestigationState.export_result,
                        readonly=True,
                        rows="10",
                        class_name="w-full px-3 py-2 border rounded-lg text-xs font-mono bg-gray-50 resize-none"
                    ),
                    rx.el.p("Copy the data above to save it.", class_name="text-xs text-gray-500 mt-2"),
                    class_name="mt-3"
                )
            ),
            class_name="mb-4"
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl mb-6"
    )


def investigation_page() -> rx.Component:
    gated_content = rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            rx.el.h1(
                "Investigation Tools",
                class_name="text-2xl font-bold text-gray-900 mb-2",
            ),
            rx.el.p(
                "Access powerful OSINT utilities for thorough and ethical data gathering.",
                class_name="text-gray-500 mb-4",
            ),
            export_actions(),
            tools_tabs(),
            class_name="max-w-5xl mx-auto",
        ),
        rx.el.div(
            rx.el.h1(
                "Authentication Required",
                class_name="text-2xl font-bold text-gray-900 mb-2",
            ),
            rx.el.p(
                "Please log in first to begin investigations.",
                class_name="text-gray-500 mb-6",
            ),
            rx.el.a(
                "Go to Login",
                href="/login",
                class_name="inline-block px-5 py-3 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800",
            ),
            class_name="max-w-md mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100",
        ),
    )
    return rx.el.div(
        sidebar(active_item="Investigations"),
        rx.el.main(
            header(),
            rx.el.div(
                gated_content,
                class_name="p-6 lg:p-8 w-full",
            ),
            class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
        ),
        class_name="flex min-h-screen bg-gray-50",
    )