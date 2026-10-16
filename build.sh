#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

echo "=========================================="
echo " Starting Render Build for Qarz Daftar Pro"
echo "=========================================="

# Check if running from repository root or backend folder
if [ -f "manage.py" ]; then
    MANAGE_CMD="python manage.py"
    REQ_FILE="requirements.txt"
elif [ -f "backend/manage.py" ]; then
    MANAGE_CMD="python backend/manage.py"
    REQ_FILE="backend/requirements.txt"
else
    echo "ERROR: manage.py not found!"
    exit 1
fi

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing Python dependencies from $REQ_FILE..."
pip install -r "$REQ_FILE"

echo "==> Collecting static files..."
$MANAGE_CMD collectstatic --no-input

echo "==> Applying database migrations..."
$MANAGE_CMD migrate --no-input

# Optional: Auto-create initial admin if environment variables are provided
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "==> Auto-creating initial admin user ($ADMIN_EMAIL)..."
    $MANAGE_CMD setup_admin \
        --email "$ADMIN_EMAIL" \
        --password "$ADMIN_PASSWORD" \
        --superadmin \
        --shop-name "${ADMIN_SHOP_NAME:-Al-Baraka Savdo}" || true
fi

echo "=========================================="
echo " Build Completed Successfully!           "
echo "=========================================="
