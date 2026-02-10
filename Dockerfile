FROM python:3.12-slim

# Create app directory
WORKDIR /app

# Install build dependencies and runtime deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY . /app

# Ensure tracking files exist
RUN touch /app/processed_posts.json /app/liked_posts.json /app/followed_accounts.json

# Run the bot
CMD ["python", "mastodon_bot.py"]
