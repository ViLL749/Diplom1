@echo off
chcp 65001 >nul
title АРМ Автосервис

REM ── Проверка Python ──────────────────────────────────────────────────────────
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [Ошибка] Python не найден. Установите Python 3.10+ с https://python.org
    pause
    exit /b 1
)

REM ── Виртуальное окружение ────────────────────────────────────────────────────
if not exist env (
    echo Создаю виртуальное окружение... [Ожидайте]
    py -m venv env
    if %errorlevel% neq 0 (
        echo [Ошибка] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
)

echo Активация виртуального окружения...
call env\Scripts\activate
if %errorlevel% neq 0 (
    echo [Ошибка] Не удалось активировать виртуальное окружение.
    pause
    exit /b 1
)

REM ── Зависимости ──────────────────────────────────────────────────────────────
if exist requirements.txt (
    echo Установка зависимостей... [Ожидайте]
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [Ошибка] Не удалось установить зависимости.
        pause
        exit /b 1
    )
) else (
    echo [Внимание] Файл requirements.txt не найден.
)

REM ── Миграции ─────────────────────────────────────────────────────────────────
echo Применение миграций базы данных...
py mykursovik2\manage.py migrate --run-syncdb -v 0
if %errorlevel% neq 0 (
    echo [Ошибка] Не удалось применить миграции.
    pause
    exit /b 1
)

REM ── Открыть браузер через 2 секунды ──────────────────────────────────────────
echo Запуск веб-приложения...
start "" /b timeout /t 2 >nul && start "" "http://127.0.0.1:8000"

REM ── Запуск сервера ────────────────────────────────────────────────────────────
py mykursovik2\manage.py runserver
if %errorlevel% neq 0 (
    echo [Ошибка] Не удалось запустить сервер Django.
    pause
    exit /b 1
)

pause
