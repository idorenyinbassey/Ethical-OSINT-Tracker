#!/bin/bash
# Uninstall project packages from system Python (if accidentally installed there)
# then recreate the virtual environment and reinstall everything inside it.
#
# Usage:
#   ./reinstall_venv.sh          — interactive (prompts before each step)
#   ./reinstall_venv.sh --yes    — non-interactive (skip all prompts)

set -e

VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"
NONINTERACTIVE=false
[ "${1}" = "--yes" ] && NONINTERACTIVE=true

confirm() {
    $NONINTERACTIVE && return 0
    read -rp "$1 [y/N] " _ans
    [[ "$_ans" =~ ^[Yy]$ ]]
}

echo "========================================================"
echo "  Ethical OSINT Tracker — Fix / Reinstall Packages"
echo "========================================================"
echo ""
echo "This script will:"
echo "  1. Uninstall project packages from your system Python (if present)"
echo "  2. Remove the existing .venv directory"
echo "  3. Create a fresh virtual environment"
echo "  4. Install all dependencies inside the venv"
echo ""

if ! $NONINTERACTIVE; then
    confirm "Continue?" || { echo "Aborted."; exit 0; }
    echo ""
fi

if [ ! -f "$REQUIREMENTS" ]; then
    echo "ERROR: $REQUIREMENTS not found. Run this script from the project root."
    exit 1
fi

# ── Step 1: Uninstall from system Python ────────────────────────────────────
echo "[1/4] Checking for packages installed in system Python..."

# Extract plain package names — strip comments, blank lines, version specs, extras
PACKAGES=$(grep -v '^\s*#' "$REQUIREMENTS" \
    | grep -v '^\s*$' \
    | sed 's/#.*//' \
    | sed 's/\[.*\]//' \
    | sed 's/[>=<!].*//' \
    | tr -d ' ' \
    | grep -v '^$')

FOUND_SYSTEM=()
for pkg in $PACKAGES; do
    # pip3 show exits 0 if installed, 1 if not
    if pip3 show "$pkg" &>/dev/null 2>&1; then
        FOUND_SYSTEM+=("$pkg")
    fi
done

if [ ${#FOUND_SYSTEM[@]} -eq 0 ]; then
    echo "  No project packages found in system Python — nothing to uninstall."
else
    echo "  Found in system Python: ${FOUND_SYSTEM[*]}"
    if confirm "  Uninstall these from system Python?"; then
        for pkg in "${FOUND_SYSTEM[@]}"; do
            echo "  Removing: $pkg"
            pip3 uninstall -y "$pkg" 2>/dev/null \
                || echo "  Warning: could not remove $pkg (may need sudo, or it was a dependency of another package)"
        done
        echo "  System uninstall done."
    else
        echo "  Skipping system uninstall."
    fi
fi
echo ""

# ── Step 2: Remove existing venv ────────────────────────────────────────────
echo "[2/4] Removing existing virtual environment..."
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo "  Removed $VENV_DIR"
else
    echo "  No existing venv found — skipping."
fi
echo ""

# ── Step 3: Create fresh venv ───────────────────────────────────────────────
echo "[3/4] Creating fresh virtual environment..."
python3 -m venv "$VENV_DIR"
echo "  Created $VENV_DIR using $(python3 --version)"
echo ""

# ── Step 4: Install into venv ───────────────────────────────────────────────
echo "[4/4] Installing packages into virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
echo ""

echo "========================================================"
echo "  Done! All packages are now isolated inside .venv/"
echo "========================================================"
echo ""
echo "  To verify:  .venv/bin/pip list"
echo "  To launch:  ./start.sh"
echo ""
