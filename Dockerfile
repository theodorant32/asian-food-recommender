FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data/ ./data/
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY railway_start.py .

# Copy Streamlit config to root level where Streamlit expects it
RUN mkdir -p .streamlit && cp frontend/.streamlit/config.toml .streamlit/

EXPOSE 8000

CMD ["python", "railway_start.py"]
