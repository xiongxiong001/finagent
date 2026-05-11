#!/usr/bin/env bash
# 一键启动开发环境
set -e

echo "🐳 启动基础设施..."
docker-compose up -d

echo "⏳ 等待服务就绪..."
sleep 3

echo "🚀 启动 FastAPI 服务..."
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000