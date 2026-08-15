FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Koyeb / Render sets PORT env variable automatically)
EXPOSE 8088

# Run headless 24/7 server
CMD ["python", "server.py"]
