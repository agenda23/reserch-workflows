FROM node:20-alpine

WORKDIR /app

# 依存定義ファイルのコピー
COPY package.json package-lock.json* ./

# 依存パッケージのインストール
RUN npm install --legacy-peer-deps

# ソースコードのコピー
COPY . .

EXPOSE 5173

# Vite開発サーバーを外部ホストからアクセス可能な形で起動 (--host)
CMD ["npm", "run", "dev", "--", "--host"]
