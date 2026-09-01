#!/usr/bin/env bash
# 用 railway up 部署時，必須喺各自子目錄執行，
# 令上傳嘅 snapshot 根目錄就係含 Dockerfile 嗰層。
set -euo pipefail

case "${1:-all}" in
  api)  (cd backend  && railway up --service api)  ;;
  web)  (cd frontend && railway up --service web)  ;;
  all)  (cd backend  && railway up --service api)
        (cd frontend && railway up --service web)  ;;
  *)    echo "用法: ./deploy.sh [api|web|all]" >&2; exit 1 ;;
esac
