FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8501

# Set placeholder environment variables (will be overridden by .env file)
# ENV DB_HOST=db_host_placeholder
# ENV DB_PORT=3306
# ENV DB_USER=db_user_placeholder
# ENV DB_PASSWORD=db_password_placeholder
# ENV DB_NAME=db_name_placeholder
# ENV ANTHROPIC_API_KEY=api_key_placeholder
# ENV CLAUDE_MODEL=claude-3-haiku-20240307
# ENV API_BASE_URL=api_url_placeholder

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]