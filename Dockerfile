
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY smart_shuffle.py .
COPY chains.json .

CMD ["python", "-u", "smart_shuffle.py"]
