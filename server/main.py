from pathlib import Path

import uvicorn
from api.routes import router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Загрузка переменных окружения
load_dotenv()

# Создание директории для отчетов, если она не существует
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

# Инициализация FastAPI приложения
app = FastAPI(
    title="GitHub Code Quality Reporter API",
    description="API для анализа PR и коммитов в GitHub репозиториях",
    version="1.0.0",
    openapi_tags=[
        {"name": "GitHub", "description": "Операции с GitHub репозиториями"},
        {"name": "Tasks", "description": "Управление асинхронными задачами"},
        {"name": "Reports", "description": "Работа с отчетами"},
    ],
)

# CORS конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов для отчетов
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# Подключение маршрутов API
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
