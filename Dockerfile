FROM python:3.12-slim

# Create a non-privileged user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY target_app /app/target_app
COPY engine_zero_agent.py /app/
COPY engine_zero_server.py /app/

# Setup virtual environment for target_app
RUN python3 -m venv /app/target_app/.venv && \
    /app/target_app/.venv/bin/pip install pytest flask

# Change ownership of /app
RUN chown -R appuser:appuser /app

# Switch to the non-privileged user
USER appuser

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run the server
CMD ["python3", "engine_zero_server.py"]
