FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clear torch cache
RUN rm -rf /root/.cache/torch || true
RUN rm -rf /root/.cache/huggingface || true

# Copy only necessary files
COPY data/ ./data/
COPY src/ ./src/
COPY run_server.py .

EXPOSE 8000

CMD ["python", "run_server.py"]
