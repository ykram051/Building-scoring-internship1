FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install PostgreSQL client libraries
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./
COPY scripts/ ./scripts/

# Set environment variables
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=building_analytics
ENV DB_USER=postgres
ENV DB_PASSWORD=postgres
ENV STRICT_DB_MODE=true

# Expose port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "main.py"]
