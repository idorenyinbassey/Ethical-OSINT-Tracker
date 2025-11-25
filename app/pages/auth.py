import reflex as rx
from app.states.auth_state import AuthState
from app.components.layout import sidebar, header


def login_form() -> rx.Component:
    return rx.el.div(
        rx.el.h1("Login", class_name="text-2xl font-bold text-gray-900 mb-4"),
        rx.el.p(
            "Authenticate to access live investigation capabilities (currently mock).",
            class_name="text-sm text-gray-500 mb-6",
        ),
        rx.el.div(
            rx.el.label(
                "Username",
                class_name="text-xs font-semibold text-gray-600 uppercase tracking-wider",
            ),
            rx.el.input(
                placeholder="admin",
                on_change=AuthState.set_username,
                value=AuthState.username_input,  # reactive binding
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
                placeholder="changeme",
                on_change=AuthState.set_password,
                value=AuthState.password_input,  # reactive binding
                class_name="w-full mt-1 px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm outline-none focus:ring-2 focus:ring-orange-100",
            ),
            class_name="mb-6",
        ),
        rx.el.button(
            rx.cond(AuthState.is_authenticated, "Logged In", "Login"),
            on_click=AuthState.login,
            disabled=AuthState.is_authenticated,
            class_name="w-full bg-gray-900 text-white py-3 rounded-xl text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-70",
        ),
        rx.cond(
            AuthState.login_error != "",
            rx.el.p(AuthState.login_error, class_name="text-sm text-red-600 mt-4"),
        ),
        rx.cond(
            AuthState.is_authenticated,
            rx.el.button(
                "Logout",
                on_click=AuthState.logout,
                class_name="w-full mt-4 bg-white border border-gray-300 text-gray-700 py-3 rounded-xl text-sm font-medium hover:bg-gray-50",
            ),
        ),
        rx.el.div(
            rx.el.span("Don't have an account? ", class_name="text-sm text-gray-600"),
            rx.el.a(
                "Register here",
                href="/register",
                class_name="text-sm text-orange-600 hover:text-orange-700 font-medium",
            ),
            class_name="mt-6 text-center",
        ),
        class_name="max-w-md mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100",
    )


def auth_page() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.fragment(
            rx.script("window.location.href = '/'"),
        ),
        rx.el.div(
            sidebar(active_item="Login"),
            rx.el.main(
                header(),
                rx.el.div(login_form(), class_name="p-6 lg:p-8 w-full flex justify-center"),
                class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']",
            ),
            class_name="flex min-h-screen bg-gray-50",
        ),
    )
