import reflex as rx
from app.components.layout import sidebar, header
from app.states.case_state import CaseState
from app.states.auth_state import AuthState


def case_card(item) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(item["title"], class_name="text-sm font-semibold text-gray-900"),
            rx.el.span(item["status"].title(), class_name="text-xs px-2 py-0.5 rounded bg-gray-100 ml-auto"),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(
            rx.cond(
                item["description"].length() > 140,
                item["description"][:140] + "...",
                item["description"]
            ),
            class_name="text-xs text-gray-600 mt-2"
        ),
        rx.el.div(
            rx.el.span("Priority: " + item["priority"].title(), class_name="text-[11px] text-gray-500"),
            rx.el.button(
                rx.icon("trash-2", class_name="w-4 h-4"),
                on_click=lambda: CaseState.delete_case_action(item["id"]),
                class_name="p-1.5 rounded hover:bg-red-50 text-gray-500 hover:text-red-600 ml-auto",
            ),
            class_name="flex items-center mt-3",
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl hover:shadow-sm transition",
    )


def case_form() -> rx.Component:
    return rx.el.div(
        rx.el.h2("Create Case", class_name="text-sm font-semibold text-gray-800 mb-3"),
        rx.el.input(
            placeholder="Title",
            value=CaseState.form_title,
            on_change=CaseState.set_form_title,
            class_name="w-full mb-2 px-3 py-2 border rounded-lg text-sm"
        ),
        rx.el.textarea(
            placeholder="Description",
            value=CaseState.form_description,
            on_change=CaseState.set_form_description,
            rows="3",
            class_name="w-full mb-2 px-3 py-2 border rounded-lg text-sm resize-none"
        ),
        rx.el.select(
            rx.el.option("low"),
            rx.el.option("medium"),
            rx.el.option("high"),
            rx.el.option("critical"),
            value=CaseState.form_priority,
            on_change=CaseState.set_form_priority,
            class_name="w-full mb-3 px-3 py-2 border rounded-lg text-sm"
        ),
        rx.cond(
            CaseState.form_error,
            rx.el.p(CaseState.form_error, class_name="text-xs text-red-600 mb-2"),
        ),
        rx.el.button(
            rx.cond(CaseState.is_loading, rx.spinner(size="1"), "Create"),
            on_click=CaseState.create_case_action,
            disabled=CaseState.is_loading,
            class_name="px-3 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium"
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl"
    )


def export_actions() -> rx.Component:
    """Export and generate actions for cases"""
    return rx.el.div(
        rx.el.h3("Export Cases", class_name="text-sm font-semibold text-gray-800 mb-2"),
        rx.el.div(
            rx.el.button(
                rx.cond(
                    CaseState.is_exporting,
                    rx.spinner(size="1"),
                    rx.el.div(
                        rx.icon("download", class_name="w-4 h-4"),
                        "Export JSON",
                        class_name="flex items-center gap-2"
                    )
                ),
                on_click=lambda: CaseState.export_cases("json"),
                disabled=CaseState.is_exporting,
                class_name="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
            ),
            rx.el.button(
                rx.cond(
                    CaseState.is_exporting,
                    rx.spinner(size="1"),
                    rx.el.div(
                        rx.icon("download", class_name="w-4 h-4"),
                        "Export CSV",
                        class_name="flex items-center gap-2"
                    )
                ),
                on_click=lambda: CaseState.export_cases("csv"),
                disabled=CaseState.is_exporting,
                class_name="px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
            ),
            class_name="flex gap-2"
        ),
        rx.cond(
            CaseState.export_result.length() > 0,
            rx.el.div(
                rx.el.textarea(
                    value=CaseState.export_result,
                    readonly=True,
                    rows="10",
                    class_name="w-full px-3 py-2 border rounded-lg text-xs font-mono bg-gray-50 resize-none"
                ),
                rx.el.p("Copy the data above to save it.", class_name="text-xs text-gray-500 mt-2"),
                class_name="mt-3"
            )
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl mb-6"
    )


def cases_page() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            sidebar(active_item="Cases"),
            rx.el.main(
                header(),
                rx.el.div(
                    rx.el.h1("Cases", class_name="text-2xl font-bold text-gray-900 mb-4"),
                    export_actions(),
                    rx.el.div(
                        case_form(),
                        class_name="mb-6"
                    ),
                    rx.el.div(
                        rx.cond(
                            CaseState.cases.length() > 0,
                            rx.el.div(
                                rx.foreach(CaseState.cases, case_card),
                                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                            ),
                            rx.el.div(
                                rx.icon("folder", class_name="w-12 h-12 text-gray-300 mb-2"),
                                rx.el.p("No cases yet", class_name="text-sm text-gray-500"),
                                class_name="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200"
                            )
                        ),
                        class_name=""
                    ),
                    on_mount=CaseState.load_cases,
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
