@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Cleaning up previous builds...
rmdir /s /q dist build

echo Building executable...
pyinstaller --noconfirm --onedir --windowed --add-data "templates;templates" --add-data "static;static" --hidden-import "engineio.async_drivers.threading" --name "ChatRoom" app.py

echo Done! The executable is in dist\ChatRoom\ChatRoom.exe
pause
