# FROM python:3.11-slim

# # Install necessary system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     default-libmysqlclient-dev \
#     libmariadb-dev \
#     wget \
#     unzip \
#     curl \
#     gnupg \
#     && rm -rf /var/lib/apt/lists/*

# # Download and install Google Chrome 116.0.5845.96 manually
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#   && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
# RUN apt-get update && apt-get -y install google-chrome-stable

# # Download and set up ChromeDriver 116.0.5845.96
# RUN wget -O /tmp/chromedriver.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/116.0.5845.96/linux64/chromedriver-linux64.zip \
#     && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
#     && rm /tmp/chromedriver.zip

# # Set environment variables
# ENV PATH="/usr/local/bin/chromedriver-linux64:${PATH}"


# # Set working directory
# WORKDIR /app

# # Copy and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Copy environment file
# COPY .env .env

# # Expose the application port
# EXPOSE 8000

# # Start the application
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.11-slim

# 安裝必要的系統依賴項
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libmariadb-dev \
    wget \
    unzip \
    curl \
    gnupg \
    --fix-missing \
    && rm -rf /var/lib/apt/lists/*

# 添加 Google Chrome 的 GPG 密鑰並設置存儲庫
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 下載並解壓 ChromeDriver
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/127.0.6533.99/linux64/chromedriver-linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

# 設置環境變量
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver-linux64/chromedriver
ENV PATH=$PATH:/usr/local/bin:/usr/local/bin/google-chrome

# 設置工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝 Python 依賴項
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程序代碼
COPY . .

EXPOSE 8080

# 啟動應用程序
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]