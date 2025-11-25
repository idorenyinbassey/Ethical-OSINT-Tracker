import reflex as rx
from app.states.auth_state import AuthState
from app.components.layout import sidebar, header


def register_form() -> rx.Component:
    return rx.el.div(
        rx.el.h1("Create Account", class_name="text-2xl font-bold text-gray-900 mb-2"),
        rx.el.p(
            "Register to access OSINT investigation tools",
            class_name="text-sm text-gray-500 mb-6",
        ),
        rx.el.div(
            rx.el.label(
                "Username",
                class_name="text-xs font-semibold text-gray-600 uppercase tracking-wider",
            ),
            rx.el.input(
                placeholder="Choose a username",
                on_change=AuthState.set_username,
                default_value=AuthState.username_input,
                class_name="w-full mt-1 px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm outline-none focus:ring-2 focus:ring-orange-100",
            ),
            class_name="mb-4",
        ),
        rx.el.div(
            rx.el.label(
                "Password",
                class_name="text-xs font-semibold text-gray-600 uppercase tracking-wider",
            ),
            rx.el.input(
                type="password",
                placeholder="At least 6 characters",
                on_change=AuthState.set_password,
                default_value=AuthState.password_input,
                class_name="w-full mt-1 px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm outline-none focus:ring-2 focus:ring-orange-100",
            ),
            class_name="mb-4",
        ),
        rx.el.div(
            rx.el.label(
                "Confirm Password",
                class_name="text-xs font-semibold text-gray-600 uppercase tracking-wider",
            ),
            rx.el.input(
                type="password",
                placeholder="Re-enter password",
                on_change=AuthState.set_confirm_password,
                default_value=AuthState.confirm_password_input,
                class_name="w-full mt-1 px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm outline-none focus:ring-2 focus:ring-orange-100",
            ),
            class_name="mb-6",
        ),
        rx.el.button(
            "Create Account",
            on_click=AuthState.register,
            class_name="w-full bg-gray-900 text-white py-3 rounded-xl text-sm font-medium hover:bg-gray-800 transition-colors",
        ),
        rx.cond(
            AuthState.register_error != "",
            rx.el.div(
                rx.icon("circle-alert", class_name="w-4 h-4 mr-2"),
                rx.el.span(AuthState.register_error),
                class_name="flex items-center text-sm text-red-600 mt-4 bg-red-50 p-3 rounded-lg",
            ),
        ),
        rx.cond(
            AuthState.register_success != "",
            rx.el.div(
                rx.icon("circle-check-big", class_name="w-4 h-4 mr-2"),
                rx.el.span(AuthState.register_success),
                class_name="flex items-center text-sm text-green-600 mt-4 bg-green-50 p-3 rounded-lg",
            ),
        ),
        rx.el.div(
            rx.el.span("Already have an account? ", class_name="text-sm text-gray-600"),
            rx.el.a(
                "Login here",
                href="/login",
                class_name="text-sm text-orange-600 hover:text-orange-700 font-medium",
            ),
            class_name="mt-6 text-center",
        ),
        class_name="max-w-md mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100",
    )


def register_page() -> rx.Component:
    return rx.el.div(
        sidebar(active_item="Register"),
        rx.el.main(
            header(),
            rx.el.div(register_form(), class_name="p-6 lg:p-8 w-full flex justify-center"),
            class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
        ),
        class_name="flex min-h-screen bg-gray-50",
    )
