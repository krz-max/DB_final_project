# 使用 Python 官方的基礎映像
FROM python:3.8

# 設定工作目錄
WORKDIR /app

# 複製專案文件到工作目錄
COPY . /app

# 安裝 Flask 和其他套件
RUN pip install --no-cache-dir -r requirements.txt

# 開啟應用程式執行
CMD ["flask", "run"]
