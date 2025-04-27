@echo off
chcp 65001 >nul

REM Проверка, существует ли виртуальное окружение
if not exist env (
    echo Создаю виртуальное окружение... [Ожидайте]
    py -m venv env
    if %errorlevel% neq 0 (
        echo [Ошибка] Не удалось создать виртуальное окружение.
        pause
        exit /b
    )
)

REM Активируем виртуальное окружение
if exist env\Scripts\activate (
    echo Активация виртуального окружения [Ожидайте]
    call env\Scripts\activate
) else (
    echo [Ошибка] Не удалось найти виртуальное окружение.
    pause
    exit /b
)

REM Установка зависимостей
if exist requirements.txt (
    echo Установка зависимостей [Ожидайте]
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [Ошибка] Не удалось установить зависимости.
        pause
        exit /b
    )
) else (
    echo [Внимание] Файл requirements.txt не найден.
)

REM Запуск проекта
echo Запуск веб-приложения.
py mykursovik2/manage.py runserver
if %errorlevel% neq 0 (
    echo [Ошибка] Не удалось запустить сервер разработки Django.
    pause
    exit /b
)

REM Удерживаем окно открытым
pause
