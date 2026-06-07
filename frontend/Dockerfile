FROM node:20-alpine

WORKDIR /app

# 依存定義ファイルのコピー
COPY package.json package-lock.json* ./

# 依存パッケージのインストール
RUN npm install --legacy-peer-deps

# ソースコードのコピー
COPY . .

ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
