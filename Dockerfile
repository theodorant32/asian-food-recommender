FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code (no models)
COPY . .

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000

# Download model at startup, not build time
CMD ["./start.sh"]
