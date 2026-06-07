#!/usr/bin/env sh
set -e

ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:5173}"
MAX_WAIT="${MAX_WAIT:-300}"

open_browser() {
  if command -v open >/dev/null 2>&1; then
    open "$DASHBOARD_URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$DASHBOARD_URL"
  elif command -v start >/dev/null 2>&1; then
    start "$DASHBOARD_URL"
  else
    echo "ブラウザを自動で開けませんでした。手動でアクセスしてください: $DASHBOARD_URL"
    return 1
  fi
}

wait_for_dashboard() {
  echo "ダッシュボード (${DASHBOARD_URL}) の起動を待っています..."
  elapsed=0
  while ! curl -sf "$DASHBOARD_URL" >/dev/null 2>&1; do
    elapsed=$((elapsed + 1))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
      echo "エラー: ${MAX_WAIT} 秒以内にフロントエンドが応答しませんでした。"
      exit 1
    fi
    sleep 1
  done
  open_browser
  echo "ダッシュボードを開きました: $DASHBOARD_URL"
}

# フォアグラウンド起動: docker compose up
if [ "$1" = "up" ] && [ "$2" != "-d" ] && [ "$2" != "--detach" ]; then
  wait_for_dashboard &
  docker compose up "${@:2}"
  exit $?
fi

# デフォルト / バックグラウンド起動
if [ "$1" = "up" ]; then
  shift
fi

docker compose up -d --build "$@"
wait_for_dashboard
