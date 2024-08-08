# 使用基础镜像
FROM python:3.11-slim

WORKDIR /app

# 安装必要的系统依赖项
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev gcc wget unzip

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY .env .env

ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
