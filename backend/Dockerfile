FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# pipのアップグレード
RUN pip install --no-cache-dir --upgrade pip

# PyTorchのCPU版を優先インストールし、GPU版によるイメージ肥大化（数GB）を防ぐ
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# requirements.txtのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザ（Chromium）のインストール
RUN playwright install chromium

# アプリケーションソースコードのコピー
COPY . .

# データベース保存用ディレクトリの作成
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
