
import streamlit.web.cli as stcli
import sys
import os

def print_startup_message():
    """Выводит сообщение с информацией по запуску приложения"""
    print("\n" + "="*60)
    print("ЗАПУСК TABLS")
    print("="*60)
    print("После запуска сервера, откройте в браузере адрес:")
    print("http://localhost:8080 или http://127.0.0.1:8080")
    print("="*60 + "\n")

if __name__ == "__main__":
    print_startup_message()
    sys.argv = [
        "streamlit", 
        "run", 
        "app.py", 
        "--server.port=8080", 
        "--server.address=0.0.0.0",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.maxUploadSize=10",
        "--browser.serverAddress=0.0.0.0",
        "--browser.gatherUsageStats=false"
    ]
    sys.exit(stcli.main())
