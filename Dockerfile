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
RUN wget -O /tmp/chromedriver.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/129.0.6668.66/linux64/chromedriver-linux64.zip \
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