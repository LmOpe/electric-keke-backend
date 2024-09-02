#!/bin/bash
# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
