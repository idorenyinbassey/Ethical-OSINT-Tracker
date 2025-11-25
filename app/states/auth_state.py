import reflex as rx
from argon2 import PasswordHasher
from app.repositories import user_repository
from app.db import init_db
from app.repositories.user_repository import create_user, get_by_username

_ph = PasswordHasher()
_demo_created = False


class AuthState(rx.State):
    is_authenticated: bool = False
    current_user: str = ""
    current_user_id: int | None = None
    login_error: str = ""
    register_error: str = ""
    register_success: str = ""
    username_input: str = ""
    password_input: str = ""
    confirm_password_input: str = ""

    @rx.event
    def set_username(self, v: str):
        self.username_input = v

    @rx.event
    def set_password(self, v: str):
        self.password_input = v

    @rx.event
    def set_confirm_password(self, v: str):
        self.confirm_password_input = v

    def _ensure_demo_user(self):
        global _demo_created
        if _demo_created:
            return
        init_db()
        existing = get_by_username("admin")
        if not existing:
            create_user("admin", _ph.hash("changeme"))
        _demo_created = True

    @rx.event
    def login(self):
        self._ensure_demo_user()
        self.login_error = ""
        
        # Normalize inputs
        username = (self.username_input or "").strip()
        password = (self.password_input or "").strip()
        
        # Debug logging
        print(f"[LOGIN] Attempting login for username: '{username}' (length: {len(username)})")
        print(f"[LOGIN] Password length: {len(password)}")
        
        if not username or not password:
            self.login_error = "Enter username and password"
            print("[LOGIN] Empty username or password")
            return
        
        user = get_by_username(username)
        if not user:
            self.login_error = "Invalid credentials"
            print(f"[LOGIN] User not found: '{username}'")
            return
        
        print(f"[LOGIN] User found: {user.username} (ID: {user.id})")
        
        try:
            _ph.verify(user.password_hash, password)
            print("[LOGIN] Password verification SUCCESS")
        except Exception as e:
            self.login_error = "Invalid credentials"
            print(f"[LOGIN] Password verification FAILED: {e}")
            return
        
        self.is_authenticated = True
        self.current_user = user.username
        self.current_user_id = user.id
        self.username_input = ""
        self.password_input = ""
        print(f"[LOGIN] Authentication successful for: {user.username}")
        return rx.redirect("/")

    @rx.event
    def register(self):
        self._ensure_demo_user()
        self.register_error = ""
        self.register_success = ""
        
        # Validation
        if not self.username_input or not self.password_input:
            self.register_error = "Username and password are required"
            return
        
        if len(self.username_input) < 3:
            self.register_error = "Username must be at least 3 characters"
            return
        
        if len(self.password_input) < 6:
            self.register_error = "Password must be at least 6 characters"
            return
        
        if self.password_input != self.confirm_password_input:
            self.register_error = "Passwords do not match"
            return
        
        # Check if user exists
        existing = get_by_username(self.username_input)
        if existing:
            self.register_error = "Username already taken"
            return
        
        # Create user
        try:
            create_user(self.username_input, _ph.hash(self.password_input))
            self.register_success = "Account created successfully! You can now login."
            self.username_input = ""
            self.password_input = ""
            self.confirm_password_input = ""
        except Exception as e:
            self.register_error = f"Registration failed: {str(e)}"

    @rx.event
    def logout(self):
        self.is_authenticated = False
        self.current_user = ""
        self.current_user_id = None
        self.username_input = ""
        self.password_input = ""
        self.confirm_password_input = ""
        self.login_error = ""
        self.register_error = ""
        self.register_success = ""
