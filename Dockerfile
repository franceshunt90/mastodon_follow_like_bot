FROM python:3.12-slim

# Add labels for Docker/Portainer metadata
LABEL org.opencontainers.image.title="Mastodon Repost Bot"
LABEL org.opencontainers.image.description="Automatically reposts and likes posts from specified Mastodon accounts"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="michael"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Create app directory
WORKDIR /app

# Install build dependencies and runtime deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY . /app

# Ensure tracking files exist and are writable
RUN mkdir -p /app && \
    touch /app/processed_posts.json /app/liked_posts.json /app/followed_accounts.json && \
    chmod -R 755 /app

# Health check to monitor bot availability
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app') else 1)" || exit 1

# Run the bot
CMD ["python", "mastodon_bot.py"]
