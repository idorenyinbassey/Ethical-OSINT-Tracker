import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode must be explicitly enabled via FLASK_DEBUG environment variable
    # Default is production-safe (no debug mode)
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"

    # Development server binds to localhost only for security
    # Use 0.0.0.0 only if explicitly set via environment variable
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "3000"))

    app.run(debug=debug_mode, host=host, port=port)
