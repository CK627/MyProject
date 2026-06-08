from setuptools import setup

APP = ['app.py']
DATA_FILES = ['templates', 'static']
OPTIONS = {
    'argv_emulation': False,
    'packages': ['flask', 'flask_socketio', 'engineio', 'socketio', 'requests', 'tkinter', 'multiprocessing', 'charset_normalizer'],
    'includes': ['engineio.async_drivers.threading', 'charset_normalizer'],
    'plist': {
        'CFBundleName': 'ChatRoom',
        'CFBundleDisplayName': 'ChatRoom',
        'CFBundleGetInfoString': "ChatRoom Application",
        'CFBundleIdentifier': "com.chatroom.app",
        'CFBundleVersion': "0.1.0",
        'CFBundleShortVersionString': "0.1.0",
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
