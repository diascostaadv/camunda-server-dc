FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do worker
COPY . /app/cpj_api_worker
COPY ../common /app/common

WORKDIR /app/cpj_api_worker

CMD ["python", "main.py"]
