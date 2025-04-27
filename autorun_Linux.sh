#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Проверка виртуального окружения
if [ ! -d "env" ]; then
    echo "Создаю виртуальное окружение... [Ожидайте]"
    python3 -m venv env
    if [ $? -ne 0 ]; then
        echo "[Ошибка] Не удалось создать виртуальное окружение."
        exit 1
    fi
fi

# Активация виртуального окружения
if [ -f "env/bin/activate" ]; then
    echo "Активация виртуального окружения [Ожидайте]"
    source env/bin/activate
else
    echo "[Ошибка] Не найдено виртуальное окружение."
    exit 1
fi

# Установка зависимостей
if [ -f "requirements.txt" ]; then
    echo "Установка зависимостей [Ожидайте]"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[Ошибка] Не удалось установить зависимости."
        deactivate
        exit 1
    fi
else
    echo "[Внимание] Файл requirements.txt не найден."
fi

# Запуск сервера
echo "Запуск веб-приложения."
python3 mykursovik2/manage.py runserver
if [ $? -ne 0 ]; then
    echo "[Ошибка] Не удалось запустить сервер разработки Django."
    deactivate
    exit 1
fi

deactivate
