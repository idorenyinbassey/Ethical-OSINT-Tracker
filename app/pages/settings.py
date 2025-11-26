import reflex as rx
from app.components.layout import sidebar, header
from app.states.settings_state import SettingsState, API_SERVICES
from app.states.auth_state import AuthState


def api_service_card(service_key: str, service_info: dict) -> rx.Component:
    """Card for each available API service"""
    return rx.el.div(
        rx.el.div(
            rx.icon("plug", class_name="w-6 h-6 text-orange-500"),
            rx.el.div(
                rx.el.h3(
                    service_info["name"],
                    class_name="text-sm font-semibold text-gray-900",
                ),
                rx.el.p(
                    service_info["description"],
                    class_name="text-xs text-gray-600 mt-1",
                ),
                class_name="ml-3 flex-1",
            ),
            class_name="flex items-start",
        ),
        rx.el.div(
            rx.el.a(
                "Docs",
                href=service_info["docs_url"],
                target="_blank",
                class_name="text-xs text-blue-500 hover:text-blue-600 mr-3",
            ),
            rx.el.button(
                "Configure",
                on_click=lambda: SettingsState.select_service(service_key),
                class_name="px-3 py-1.5 bg-orange-500 text-white text-xs font-medium rounded-lg hover:bg-orange-600 transition-colors",
            ),
            class_name="flex items-center mt-3",
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-shadow",
    )


def configured_api_card(config) -> rx.Component:
    """Card for configured API"""
    service_info = API_SERVICES.get(config["service_name"], {})
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.cond(
                    config["is_enabled"],
                    rx.el.div(
                        class_name="w-2 h-2 bg-green-500 rounded-full"
                    ),
                    rx.el.div(
                        class_name="w-2 h-2 bg-gray-400 rounded-full"
                    ),
                ),
                rx.el.div(
                    rx.el.h3(
                        service_info.get("name", config["service_name"]),
                        class_name="text-sm font-semibold text-gray-900",
                    ),
                    rx.el.p(
                        f"Rate limit: {config['rate_limit']}/hour",
                        class_name="text-xs text-gray-600 mt-0.5",
                    ),
                    class_name="ml-3",
                ),
                class_name="flex items-center",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", class_name="w-4 h-4"),
                    on_click=lambda: SettingsState.edit_config(config["service_name"]),
                    class_name="p-2 text-gray-600 hover:text-orange-500 hover:bg-orange-50 rounded-lg transition-colors",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="w-4 h-4"),
                    on_click=lambda: SettingsState.delete_config_action(config["service_name"]),
                    class_name="p-2 text-gray-600 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors ml-2",
                ),
                class_name="flex items-center",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.div(
            rx.el.p(
                f"API Key: {config['api_key'][:8]}...{config['api_key'][-4:]}",
                class_name="text-xs text-gray-500 mt-2",
            ),
            rx.el.p(
                config["base_url"],
                class_name="text-xs text-gray-500 mt-1 truncate",
            ),
            rx.cond(
                config["notes"],
                rx.el.p(
                    config["notes"],
                    class_name="text-xs text-gray-600 mt-2 italic",
                ),
            ),
        ),
        class_name="p-4 bg-white border border-gray-200 rounded-xl",
    )


def google_vision_setup_instructions() -> rx.Component:
    """Setup instructions specifically for Google Cloud Vision AI"""
    return rx.el.div(
        rx.el.div(
            rx.icon("info", class_name="w-5 h-5 text-blue-500 flex-shrink-0"),
            rx.el.h4(
                "Google Cloud Vision AI Setup",
                class_name="text-sm font-semibold text-gray-900",
            ),
            class_name="flex items-center gap-2 mb-3",
        ),
        rx.el.ol(
            rx.el.li(
                rx.el.span("Go to ", class_name="text-xs text-gray-600"),
                rx.el.a(
                    "Google Cloud Console",
                    href="https://console.cloud.google.com",
                    target="_blank",
                    class_name="text-xs text-blue-500 hover:text-blue-600 underline",
                ),
                class_name="mb-2",
            ),
            rx.el.li(
                "Create a new project or select an existing one",
                class_name="text-xs text-gray-600 mb-2",
            ),
            rx.el.li(
                rx.el.span("Navigate to ", class_name="text-xs text-gray-600"),
                rx.el.strong("APIs & Services", class_name="text-xs text-gray-800"),
                rx.el.span(" → ", class_name="text-xs text-gray-600"),
                rx.el.strong("Library", class_name="text-xs text-gray-800"),
                class_name="mb-2",
            ),
            rx.el.li(
                rx.el.span("Search for ", class_name="text-xs text-gray-600"),
                rx.el.strong("\"Cloud Vision API\"", class_name="text-xs text-gray-800"),
                rx.el.span(" and enable it", class_name="text-xs text-gray-600"),
                class_name="mb-2",
            ),
            rx.el.li(
                rx.el.span("Go to ", class_name="text-xs text-gray-600"),
                rx.el.strong("APIs & Services", class_name="text-xs text-gray-800"),
                rx.el.span(" → ", class_name="text-xs text-gray-600"),
                rx.el.strong("Credentials", class_name="text-xs text-gray-800"),
                class_name="mb-2",
            ),
            rx.el.li(
                rx.el.span("Click ", class_name="text-xs text-gray-600"),
                rx.el.strong("\"Create Credentials\"", class_name="text-xs text-gray-800"),
                rx.el.span(" → ", class_name="text-xs text-gray-600"),
                rx.el.strong("API Key", class_name="text-xs text-gray-800"),
                class_name="mb-2",
            ),
            rx.el.li(
                "Copy the generated API key and paste it below",
                class_name="text-xs text-gray-600 mb-2",
            ),
            rx.el.li(
                rx.el.span("(Optional) Restrict the key to ", class_name="text-xs text-gray-600"),
                rx.el.strong("Cloud Vision API", class_name="text-xs text-gray-800"),
                rx.el.span(" only for security", class_name="text-xs text-gray-600"),
                class_name="mb-0",
            ),
            class_name="list-decimal list-inside space-y-1",
        ),
        # API Key Format Requirements
        rx.el.div(
            rx.icon("circle-alert", class_name="w-4 h-4 text-orange-600 flex-shrink-0"),
            rx.el.div(
                rx.el.p(
                    "API Key Format Requirements:",
                    class_name="text-xs font-semibold text-orange-800 mb-1",
                ),
                rx.el.ul(
                    rx.el.li(
                        "Must start with 'AIza'",
                        class_name="text-xs text-orange-700",
                    ),
                    rx.el.li(
                        "Exactly 39 characters long",
                        class_name="text-xs text-orange-700",
                    ),
                    rx.el.li(
                        rx.el.span("Example: ", class_name="text-xs text-orange-600"),
                        rx.el.code(
                            "AIzaSyDaGmWKa4JsXZ-HjGbvB0123456789ABCD",
                            class_name="text-xs bg-orange-100 px-1 py-0.5 rounded font-mono",
                        ),
                        class_name="text-xs text-orange-700",
                    ),
                    class_name="list-disc list-inside ml-2 space-y-0.5",
                ),
                class_name="flex-1",
            ),
            class_name="flex items-start gap-2 mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200",
        ),
        # Common Issues Section
        rx.el.div(
            rx.icon("triangle-alert", class_name="w-4 h-4 text-red-600 flex-shrink-0"),
            rx.el.div(
                rx.el.p(
                    "Common Issues & Solutions:",
                    class_name="text-xs font-semibold text-red-800 mb-1",
                ),
                rx.el.ul(
                    rx.el.li(
                        rx.el.strong("400 Bad Request: ", class_name="text-xs"),
                        rx.el.span("Invalid API key format", class_name="text-xs text-red-700"),
                        class_name="mb-1",
                    ),
                    rx.el.li(
                        rx.el.strong("401 Unauthorized: ", class_name="text-xs"),
                        rx.el.span("API key is invalid or revoked", class_name="text-xs text-red-700"),
                        class_name="mb-1",
                    ),
                    rx.el.li(
                        rx.el.strong("403 Forbidden: ", class_name="text-xs"),
                        rx.el.span("API not enabled or quota exceeded", class_name="text-xs text-red-700"),
                        class_name="mb-0",
                    ),
                    class_name="list-disc list-inside ml-2 space-y-0.5",
                ),
                class_name="flex-1",
            ),
            class_name="flex items-start gap-2 mt-2 p-3 bg-red-50 rounded-lg border border-red-200",
        ),
        rx.el.div(
            rx.icon("circle-check", class_name="w-4 h-4 text-green-500 flex-shrink-0"),
            rx.el.p(
                "Free tier: 1,000 requests/month",
                class_name="text-xs text-green-700 font-medium",
            ),
            class_name="flex items-center gap-2 mt-2 p-2 bg-green-50 rounded-lg",
        ),
        class_name="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100",
    )


def api_config_form() -> rx.Component:
    """Form for adding/editing API configuration"""
    service_info = API_SERVICES.get(SettingsState.selected_service, {})
    
    return rx.cond(
        SettingsState.show_add_form,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        f"Configure {service_info.get('name', 'API Service')}",
                        class_name="text-lg font-bold text-gray-900",
                    ),
                    rx.el.button(
                        rx.icon("x", class_name="w-5 h-5"),
                        on_click=SettingsState.cancel_form,
                        class_name="p-2 text-gray-400 hover:text-gray-600 rounded-lg",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
                # Show Google Vision setup instructions if configuring ImageRecognition
                rx.cond(
                    SettingsState.selected_service == "ImageRecognition",
                    google_vision_setup_instructions(),
                ),
                rx.el.div(
                    rx.el.label(
                        "Service Name",
                        class_name="block text-sm font-medium text-gray-700 mb-2",
                    ),
                    rx.el.input(
                        value=SettingsState.form_service_name,
                        read_only=True,
                        class_name="w-full px-4 py-2.5 bg-gray-100 border border-gray-200 rounded-xl text-sm text-gray-700",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "API Key",
                        class_name="block text-sm font-medium text-gray-700 mb-2",
                    ),
                    rx.el.input(
                        type="password",
                        placeholder="Enter your API key",
                        on_change=SettingsState.set_form_api_key,
                        value=SettingsState.form_api_key,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none",
                    ),
                    # Real-time validation message
                    rx.cond(
                        SettingsState.api_key_validation_message != "",
                        rx.el.div(
                            SettingsState.api_key_validation_message,
                            class_name=rx.cond(
                                SettingsState.api_key_validation_message.contains("✅"),
                                "text-sm text-green-600 mt-2 font-medium",
                                rx.cond(
                                    SettingsState.api_key_validation_message.contains("⚠️"),
                                    "text-sm text-orange-600 mt-2",
                                    "text-sm text-gray-500 mt-2"
                                )
                            ),
                        ),
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "Base URL",
                        class_name="block text-sm font-medium text-gray-700 mb-2",
                    ),
                    rx.el.input(
                        placeholder="https://api.example.com",
                        on_change=SettingsState.set_form_base_url,
                        value=SettingsState.form_base_url,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "Rate Limit (requests/hour)",
                        class_name="block text-sm font-medium text-gray-700 mb-2",
                    ),
                    rx.el.input(
                        type="number",
                        on_change=SettingsState.set_form_rate_limit,
                        value=SettingsState.form_rate_limit,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        "Notes (Optional)",
                        class_name="block text-sm font-medium text-gray-700 mb-2",
                    ),
                    rx.el.textarea(
                        placeholder="Add any notes about this API configuration",
                        on_change=SettingsState.set_form_notes,
                        value=SettingsState.form_notes,
                        class_name="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none resize-none",
                        rows="3",
                    ),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label(
                        rx.el.input(
                            type="checkbox",
                            checked=SettingsState.form_is_enabled,
                            on_change=SettingsState.set_form_is_enabled,
                            class_name="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500 mr-2",
                        ),
                        "Enable this API",
                        class_name="flex items-center text-sm text-gray-700 cursor-pointer",
                    ),
                    class_name="mb-6",
                ),
                # Test API Connection Button (only for ImageRecognition)
                rx.cond(
                    SettingsState.selected_service == "ImageRecognition",
                    rx.el.div(
                        rx.el.div(
                            rx.icon("zap", size=16, class_name="text-blue-600"),
                            rx.el.span(
                                "Test Your API Key",
                                class_name="text-sm font-semibold text-gray-700",
                            ),
                            class_name="flex items-center gap-2 mb-2",
                        ),
                        rx.el.button(
                            rx.cond(
                                SettingsState.is_testing_api,
                                rx.el.div(
                                    rx.spinner(size="3"),
                                    rx.el.span("Testing...", class_name="ml-2"),
                                    class_name="flex items-center",
                                ),
                                rx.el.div(
                                    rx.icon("circle-play", size=16),
                                    rx.el.span("Test API Connection", class_name="ml-2"),
                                    class_name="flex items-center",
                                ),
                            ),
                            on_click=SettingsState.test_api_connection,
                            disabled=SettingsState.is_testing_api,
                            class_name="w-full px-4 py-2.5 bg-blue-500 text-white text-sm font-medium rounded-xl hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                        ),
                        rx.cond(
                            SettingsState.api_test_result != "",
                            rx.el.div(
                                SettingsState.api_test_result,
                                class_name=rx.cond(
                                    SettingsState.api_test_result.contains("✅"),
                                    "mt-3 p-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-700 font-medium",
                                    rx.cond(
                                        SettingsState.api_test_result.contains("⚠️"),
                                        "mt-3 p-3 rounded-lg bg-orange-50 border border-orange-200 text-sm text-orange-700",
                                        "mt-3 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700"
                                    )
                                ),
                            ),
                        ),
                        class_name="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100",
                    ),
                ),
                rx.cond(
                    SettingsState.save_error,
                    rx.el.div(
                        rx.icon("circle-alert", class_name="w-4 h-4 text-red-500 mr-2"),
                        SettingsState.save_error,
                        class_name="flex items-center text-sm text-red-600 mb-4 p-3 bg-red-50 rounded-lg",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancel",
                        on_click=SettingsState.cancel_form,
                        class_name="px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-200 transition-colors",
                    ),
                    rx.el.button(
                        rx.cond(
                            SettingsState.is_loading,
                            rx.spinner(size="1"),
                            "Save Configuration",
                        ),
                        on_click=SettingsState.save_config,
                        disabled=SettingsState.is_loading,
                        class_name="px-4 py-2.5 bg-orange-500 text-white text-sm font-medium rounded-xl hover:bg-orange-600 transition-colors ml-3",
                    ),
                    class_name="flex justify-end",
                ),
                class_name="bg-white p-6 rounded-2xl border border-gray-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4",
        ),
    )


def settings_page() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            sidebar(active_item="Settings"),
            rx.el.main(
                header(),
                api_config_form(),
                rx.el.div(
                    rx.el.div(
                        rx.el.h1(
                            "Settings",
                            class_name="text-3xl font-bold text-gray-900 mb-2",
                        ),
                        rx.el.p(
                            "Configure API integrations and system preferences",
                            class_name="text-gray-600",
                        ),
                        class_name="mb-8",
                    ),
                    # Configured APIs Section
                    rx.el.div(
                        rx.el.h2(
                            "Configured APIs",
                            class_name="text-xl font-bold text-gray-900 mb-4",
                        ),
                        rx.cond(
                            SettingsState.api_configs.length() > 0,
                            rx.el.div(
                                rx.foreach(
                                    SettingsState.api_configs,
                                    configured_api_card,
                                ),
                                class_name="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8",
                            ),
                            rx.el.div(
                                rx.icon("plug-zap", class_name="w-12 h-12 text-gray-300 mb-2"),
                                rx.el.p(
                                    "No APIs configured yet",
                                    class_name="text-sm text-gray-500",
                                ),
                                class_name="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 mb-8",
                            ),
                        ),
                    ),
                    # Available APIs Section
                    rx.el.div(
                        rx.el.h2(
                            "Available API Integrations",
                            class_name="text-xl font-bold text-gray-900 mb-4",
                        ),
                        rx.el.div(
                            *[
                                api_service_card(key, info)
                                for key, info in API_SERVICES.items()
                            ],
                            class_name="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4",
                        ),
                    ),
                    class_name="p-6 lg:p-8 max-w-[1600px] mx-auto",
                    on_mount=SettingsState.load_configs,
                ),
                class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
            ),
            class_name="flex min-h-screen bg-gray-50",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("shield-alert", class_name="w-16 h-16 text-orange-500 mb-4"),
                rx.el.h2(
                    "Authentication Required",
                    class_name="text-2xl font-bold text-gray-900 mb-2",
                ),
                rx.el.p(
                    "Please log in to access settings",
                    class_name="text-gray-600 mb-6",
                ),
                rx.el.a(
                    "Go to Login",
                    href="/login",
                    class_name="px-6 py-3 bg-orange-500 text-white font-medium rounded-xl hover:bg-orange-600 transition-colors",
                ),
                class_name="flex flex-col items-center justify-center min-h-screen p-6",
            ),
            class_name="w-full",
        ),
    )
