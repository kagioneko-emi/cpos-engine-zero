FROM python:3.12-slim

# Create a non-privileged user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY target_app /app/target_app
COPY ait_firewall /app/ait_firewall
COPY engine_zero_agent.py /app/
COPY engine_zero_server.py /app/

# Setup runtime virtual environment outside /app/target_app.
# /app/target_app is replaced by a read-only bind mount during sandbox validation,
# so putting the venv under /app/target_app would hide it at runtime.
RUN python3 -m venv /opt/engine-zero-venv && \
    /opt/engine-zero-venv/bin/pip install --no-cache-dir pytest flask
ENV PATH="/opt/engine-zero-venv/bin:$PATH"

# Change ownership of /app
RUN chown -R appuser:appuser /app

# Switch to the non-privileged user
USER appuser

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run the server
CMD ["/opt/engine-zero-venv/bin/python", "engine_zero_server.py"]
