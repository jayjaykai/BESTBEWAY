FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libmariadb-dev \
    --fix-missing \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

COPY .env .env

EXPOSE 8000
EXPOSE 9200
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]


# FROM python:3.11-slim

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     default-libmysqlclient-dev \
#     gcc \
#     wget \
#     unzip \
#     gnupg \
#   && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#   && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
#   && apt-get update \
#   && apt-get -y install google-chrome-stable

# # 设置环境变量
# ENV CHROME_BIN=/usr/bin/google-chrome
# ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# # 安装 Python 依赖项
# COPY requirements.txt requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# # 复制项目文件
# COPY . .

# # 复制环境变量文件
# COPY .env .env

# EXPOSE 8000

# # 启动应用程序
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
