FROM python:3.14-slim

# логи сразу в консоль, без .pyc файлов
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Сначала зависимости: пока requirements.txt не менялся, Docker берёт этот слой из кэша
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# запускаем не от root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Сначала миграции, потом сервер. exec нужен, чтобы uvicorn получал сигнал остановки
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]