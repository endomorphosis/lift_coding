FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy runner script
COPY runner.py .

# Make script executable
RUN chmod +x runner.py

# Run as non-root user for security
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

# Run the agent runner
CMD ["python", "runner.py"]
