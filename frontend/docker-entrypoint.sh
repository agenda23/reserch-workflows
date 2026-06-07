#!/bin/sh
set -e

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
MAX_ATTEMPTS=60

echo "バックエンド (${BACKEND_URL}) の起動を待機しています..."
attempt=0
until wget -qO- "${BACKEND_URL}/" > /dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "エラー: バックエンドが ${MAX_ATTEMPTS} 秒以内に応答しませんでした。"
    exit 1
  fi
  sleep 1
done

echo "バックエンドが起動しました。Vite開発サーバーを開始します。"
exec npm run dev -- --host
