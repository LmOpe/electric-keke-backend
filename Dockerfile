# Use the official Python 3.11 image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install pip
RUN pip install --upgrade pip

# Copy the requirements.txt file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and switch to it
RUN useradd -ms /bin/bash celeryuser

# Copy the current directory contents into the container at /app
COPY . /app/

# Set permissions to the non-root user
RUN chown -R celeryuser:celeryuser /app

# Switch to the non-root user
USER celeryuser

# Expose port 8000 for Django
EXPOSE 80

# Collect static files
RUN python manage.py collectstatic --noinput

# Run the Django development server
CMD ["daphne", "-b", "0.0.0.0", "-p", "80", "ecoride.asgi:application"]
