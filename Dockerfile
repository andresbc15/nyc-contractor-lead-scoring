FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY app ./app
COPY pipeline ./pipeline
EXPOSE 8000
CMD fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}