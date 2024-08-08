FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y chromium-browser chromium-chromedriver && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

COPY .env .env

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]