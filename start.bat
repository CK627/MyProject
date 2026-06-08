@echo off
chcp 65001 > nul

echo ===========================================
echo 宁波旅游指南网站启动脚本
echo ===========================================

REM 检查是否已存在运行的服务器进程
netstat -an | findstr ":8080 " > nul
if %errorlevel% == 0 (
    echo 错误: 端口 8080 已被占用，请关闭占用该端口的程序后再试。
    echo 您可以使用 'netstat -ano ^| findstr :8080' 查看哪个进程占用了端口
    pause
    exit /b 1
)

echo 正在启动 PHP 内置服务器...
echo 服务器将在 http://localhost:8080 上运行

REM 启动 PHP 内置服务器
REM 将根目录设置为项目目录，这样可以同时访问前端文件和后端 API
start "" cmd /c php -S localhost:8080 -t .

echo 服务器已启动
echo 访问地址: http://localhost:8080
echo.
echo 提示:
echo - 关闭此窗口将停止服务器
echo - 服务器日志将在新打开的窗口中显示
echo.
echo ===========================================
echo 按任意键继续...
pause > nul