#!/bin/bash

# 宁波旅游指南网站启动脚本
# 适用于 Unix/Linux/Mac 系统

echo "==========================================="
echo "宁波旅游指南网站启动脚本"
echo "==========================================="

# 检查是否已存在运行的服务器进程
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null; then
    echo "错误: 端口 8080 已被占用，请关闭占用该端口的程序后再试。"
    echo "您可以使用 'lsof -i :8080' 查看哪个进程占用了端口"
    exit 1
fi

echo "正在启动 PHP 内置服务器..."
echo "服务器将在 http://localhost:8080 上运行"

# 启动 PHP 内置服务器
# 将根目录设置为项目目录，这样可以同时访问前端文件和后端 API
php -S localhost:8080 -t . &

SERVER_PID=$!

echo "服务器已启动 (PID: $SERVER_PID)"
echo "访问地址: http://localhost:8080"
echo ""
echo "提示:"
echo "- 按 Ctrl+C 停止服务器"
echo "- 服务器日志将显示在此窗口中"
echo ""
echo "==========================================="

# 等待服务器进程结束
wait $SERVER_PID