import reflex as rx
from app.components.layout import sidebar, header
from app.states.auth_state import AuthState
from app.states.report_state import ReportState


def threat_badge(level: str) -> rx.Component:
    """Colored badge for threat level"""
    colors = {
        "high": "bg-red-100 text-red-700",
        "medium": "bg-orange-100 text-orange-700",
        "low": "bg-green-100 text-green-700",
    }
    return rx.el.span(
        level.capitalize(),
        class_name=f"px-2 py-1 rounded text-xs font-medium {colors.get(level, 'bg-gray-100 text-gray-700')}"
    )


def enriched_indicator_card(indicator) -> rx.Component:
    """Card displaying enriched indicator"""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(
                    rx.match(
                        indicator["type"],
                        ("domain", "globe"),
                        ("ip", "map-pin"),
                        ("email", "mail"),
                        "circle-help",
                    ),
                    class_name="w-5 h-5 text-orange-500"
                ),
                rx.el.div(
                    rx.el.p(indicator["value"], class_name="text-sm font-medium text-gray-900"),
                    rx.el.p(indicator["type"], class_name="text-xs text-gray-500"),
                    class_name="ml-3"
                ),
                class_name="flex items-center flex-1"
            ),
            threat_badge(indicator["threat_level"]),
            class_name="flex items-center justify-between mb-2"
        ),
        rx.el.div(
            rx.el.p(
                rx.cond(
                    indicator["details"],
                    rx.text(str(indicator["details"])),
                    ""
                ),
                class_name="text-xs text-gray-600"
            ),
            class_name="pl-8 space-y-1"
        ),
        class_name="p-3 bg-gray-50 rounded-lg border border-gray-200"
    )


def report_card(report) -> rx.Component:
    """Card for each report"""
    return rx.el.div(
        rx.el.div(
            rx.el.h3(report["title"], class_name="text-lg font-semibold text-gray-900 mb-2"),
            rx.el.p(
                rx.cond(report["summary"], report["summary"], "No summary provided"),
                class_name="text-sm text-gray-600 mb-3"
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("flag", class_name="w-4 h-4 text-gray-400 mr-1"),
                    rx.el.span(
                        rx.cond(
                            report['indicators'],
                            "Indicators present",
                            "No indicators"
                        ),
                        class_name="text-xs text-gray-500"
                    ),
                    class_name="flex items-center"
                ),
                rx.el.div(
                    rx.icon("calendar", class_name="w-4 h-4 text-gray-400 mr-1"),
                    rx.el.span(
                        report["created_at"][:10],
                        class_name="text-xs text-gray-500"
                    ),
                    class_name="flex items-center"
                ),
                class_name="flex items-center gap-4 mb-3"
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("trash-2", class_name="w-4 h-4"),
                    on_click=lambda: ReportState.delete_report_action(report["id"]),
                    class_name="px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium transition-colors"
                ),
                class_name="flex justify-end"
            ),
        ),
        class_name="p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md transition-shadow"
    )


def create_report_form() -> rx.Component:
    """Modal form for creating new report"""
    return rx.cond(
        ReportState.show_create_form,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3("Create Intelligence Report", class_name="text-lg font-bold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", class_name="w-5 h-5"),
                        on_click=ReportState.cancel_create_form,
                        class_name="p-2 text-gray-400 hover:text-gray-600 rounded-lg"
                    ),
                    class_name="flex items-center justify-between mb-6"
                ),
                rx.el.div(
                    rx.el.label("Title", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.input(
                        placeholder="Report title",
                        on_change=ReportState.set_form_title,
                        value=ReportState.form_title,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                    ),
                    class_name="mb-4"
                ),
                rx.el.div(
                    rx.el.label("Summary", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.textarea(
                        placeholder="Executive summary of findings",
                        on_change=ReportState.set_form_summary,
                        value=ReportState.form_summary,
                        rows="4",
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none resize-none"
                    ),
                    class_name="mb-4"
                ),
                rx.el.div(
                    rx.el.label("Indicators (comma-separated)", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.textarea(
                        placeholder="example.com, 192.168.1.1, user@domain.com",
                        on_change=ReportState.set_form_indicators_raw,
                        value=ReportState.form_indicators_raw,
                        rows="3",
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none resize-none"
                    ),
                    class_name="mb-4"
                ),
                rx.el.div(
                    rx.el.label("Related Case ID (optional)", class_name="block text-sm font-medium text-gray-700 mb-2"),
                    rx.el.input(
                        type="number",
                        placeholder="Case ID",
                        on_change=ReportState.set_form_related_case_id,
                        value=ReportState.form_related_case_id,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                    ),
                    class_name="mb-6"
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancel",
                        on_click=ReportState.cancel_create_form,
                        class_name="px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-200 transition-colors"
                    ),
                    rx.el.button(
                        rx.cond(ReportState.is_creating, rx.spinner(size="1"), "Create Report"),
                        on_click=ReportState.create_new_report,
                        disabled=ReportState.is_creating,
                        class_name="px-4 py-2.5 bg-orange-500 text-white text-sm font-medium rounded-xl hover:bg-orange-600 transition-colors ml-3"
                    ),
                    class_name="flex justify-end"
                ),
                class_name="bg-white p-6 rounded-2xl border border-gray-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            ),
            class_name="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        )
    )


def report_page() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            sidebar(active_item="Reports"),
            rx.el.main(
                header(),
                create_report_form(),
                rx.el.div(
                    # Header
                    rx.el.div(
                        rx.el.h1("Intelligence Reports", class_name="text-2xl font-bold text-gray-900 mb-2"),
                        rx.el.p("Aggregate and export threat intelligence", class_name="text-gray-600"),
                        class_name="mb-6"
                    ),
                    
                    # Actions
                    rx.el.div(
                        rx.el.button(
                            rx.icon("plus", class_name="w-4 h-4 mr-2"),
                            "New Report",
                            on_click=ReportState.show_create_report_form,
                            class_name="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                        ),
                        rx.el.button(
                            rx.cond(ReportState.is_enriching, rx.spinner(size="1"), rx.icon("sparkles", class_name="w-4 h-4 mr-2")),
                            "Enrich from Investigations",
                            on_click=ReportState.enrich_from_investigations,
                            disabled=ReportState.is_enriching,
                            class_name="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                        ),
                        rx.el.button(
                            rx.cond(ReportState.is_exporting, rx.spinner(size="1"), rx.icon("download", class_name="w-4 h-4 mr-2")),
                            "Export JSON",
                            on_click=lambda: ReportState.export_reports("json"),
                            disabled=ReportState.is_exporting,
                            class_name="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                        ),
                        rx.el.button(
                            rx.icon("file-text", class_name="w-4 h-4 mr-2"),
                            "Export CSV",
                            on_click=lambda: ReportState.export_reports("csv"),
                            disabled=ReportState.is_exporting,
                            class_name="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium inline-flex items-center"
                        ),
                        class_name="flex gap-3 mb-6"
                    ),
                    
                    # Export result display
                    rx.cond(
                        ReportState.export_result,
                        rx.el.div(
                            rx.el.div(
                                rx.el.h3("Export Result", class_name="text-sm font-semibold text-gray-900 mb-2"),
                                rx.el.button(
                                    rx.icon("x", class_name="w-4 h-4"),
                                    on_click=lambda: ReportState.set_export_result(None),
                                    class_name="p-1 text-gray-400 hover:text-gray-600"
                                ),
                                class_name="flex items-center justify-between mb-2"
                            ),
                            rx.el.pre(
                                ReportState.export_result,
                                class_name="text-xs text-gray-700 bg-gray-50 p-4 rounded-lg overflow-x-auto max-h-64"
                            ),
                            class_name="mb-6 p-4 bg-white rounded-xl border border-gray-200"
                        )
                    ),
                    
                    # Enriched Indicators Section
                    rx.cond(
                        ReportState.enriched_indicators.length() > 0,
                        rx.el.div(
                            rx.el.h2("Enriched Indicators", class_name="text-xl font-bold text-gray-900 mb-4"),
                            rx.el.div(
                                rx.foreach(ReportState.enriched_indicators, enriched_indicator_card),
                                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8"
                            ),
                        )
                    ),
                    
                    # Reports List
                    rx.el.div(
                        rx.el.h2("Reports", class_name="text-xl font-bold text-gray-900 mb-4"),
                        rx.cond(
                            ReportState.reports.length() > 0,
                            rx.el.div(
                                rx.foreach(ReportState.reports, report_card),
                                class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                            ),
                            rx.el.div(
                                rx.icon("file-search", class_name="w-12 h-12 text-gray-300 mb-2"),
                                rx.el.p("No reports yet", class_name="text-sm text-gray-500"),
                                rx.el.button(
                                    "Create your first report",
                                    on_click=ReportState.show_create_report_form,
                                    class_name="mt-3 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm rounded-lg"
                                ),
                                class_name="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200"
                            )
                        ),
                    ),
                    on_mount=ReportState.load_reports,
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
