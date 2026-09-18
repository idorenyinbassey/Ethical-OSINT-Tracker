#!/bin/bash
# Shared secret-handling helpers for start.sh and the Termux launch script.
#
# Solves two problems with the old flow:
#   1. SECRET_KEY / API_KEYS_FERNET_KEY had to be generated and exported by
#      hand, or were silently random-per-restart — which logged everyone out
#      on every restart and made saving an API key in Settings crash with a
#      500 (API_KEYS_FERNET_KEY unset). These are now generated ONCE and
#      persisted to a local, gitignored secrets file so entering/using API
#      keys afterwards "just works" across restarts.
#   2. ADMIN_PASSWORD had to be typed inline as `ADMIN_PASSWORD=... ./start.sh`,
#      which most shells write verbatim into shell history in plaintext. It's
#      now prompted for with terminal echo disabled instead — nothing is
#      exposed on screen, in scrollback, or in history.
#
# Usage (from start.sh / a Termux launch script):
#   source "$(dirname "$0")/scripts/secrets_bootstrap.sh"
#   bootstrap_secrets "$FERNET_GEN_CMD"   # a full shell command that prints a Fernet key
#   ensure_admin_password                 # prompts for ADMIN_PASSWORD if not already set

SECRETS_FILE="${SECRETS_FILE:-secrets.env}"

# Generates a value for $var_name (by eval-ing the given shell command) and
# appends it to $SECRETS_FILE, unless it's already set in the environment
# or already persisted in the file. Idempotent — safe to call every run.
# Never aborts the caller on failure (callers run under `set -e`) — it
# warns and returns 1, since a missing optional secret shouldn't block the
# whole app from starting.
_ensure_secret() {
    local var_name="$1" gen_cmd="$2"

    if [ -n "${!var_name}" ]; then
        return 0
    fi
    if [ -f "$SECRETS_FILE" ] && grep -q "^${var_name}=" "$SECRETS_FILE" 2>/dev/null; then
        return 0
    fi

    echo "  Generating $var_name (first run — saved to $SECRETS_FILE for future restarts)"
    local value
    value="$(eval "$gen_cmd" 2>/dev/null)" || true
    if [ -z "$value" ]; then
        echo "  ⚠️  Could not generate $var_name automatically."
        return 1
    fi
    printf '%s=%s\n' "$var_name" "$value" >> "$SECRETS_FILE"
}

# Reads one line of input with terminal echo disabled. Falls back to a
# plain (visible) read when there's no TTY (e.g. piped/CI input), so
# non-interactive automation still works.
_prompt_secret() {
    local prompt_text="$1" __outvar="$2" value=""
    if [ -t 0 ]; then
        read -rsp "$prompt_text" value
        echo ""
    else
        read -r value
    fi
    printf -v "$__outvar" '%s' "$value"
}

# Ensures SECRET_KEY and API_KEYS_FERNET_KEY exist and are loaded into this
# shell's environment, generating + persisting them on first run.
#
# $1 is the full shell command to run to print a fresh Fernet key — this is
# the only one of the two secrets with a non-stdlib dependency
# ('cryptography'), so the caller picks whichever python/venv actually has
# it installed (the pipx-managed venv, or .venv) rather than this file
# guessing at internal venv paths.
bootstrap_secrets() {
    local fernet_gen_cmd="$1"

    touch "$SECRETS_FILE"
    chmod 600 "$SECRETS_FILE" 2>/dev/null || true

    _ensure_secret "SECRET_KEY" \
        'python3 -c "import secrets; print(secrets.token_hex(32))"' || true
    _ensure_secret "API_KEYS_FERNET_KEY" "$fernet_gen_cmd" || true

    set -a
    # shellcheck source=/dev/null
    source "$SECRETS_FILE"
    set +a
}

# Ensures ADMIN_PASSWORD is set, prompting for it (hidden, confirmed twice)
# if it wasn't already provided via the environment or a .env/secrets file.
ensure_admin_password() {
    if [ -n "$ADMIN_PASSWORD" ]; then
        return 0
    fi

    echo ""
    echo "Set the admin account password (min. 8 characters)."
    echo "Input is hidden and is never written to shell history."
    local pw1 pw2
    while true; do
        _prompt_secret "  Admin password: " pw1
        if [ "${#pw1}" -lt 8 ]; then
            echo "  Password must be at least 8 characters — try again."
            continue
        fi
        _prompt_secret "  Confirm password: " pw2
        if [ "$pw1" != "$pw2" ]; then
            echo "  Passwords did not match — try again."
            continue
        fi
        break
    done
    export ADMIN_PASSWORD="$pw1"
    # unset locals holding the plaintext password now that it's exported
    unset pw1 pw2
}
