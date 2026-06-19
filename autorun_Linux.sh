#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# ── Проверка Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[Ошибка] Python 3 не найден. Установите Python 3.10+:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# ── Виртуальное окружение ──────────────────────────────────────────────────────
if [ ! -d "env" ]; then
    echo "Создаю виртуальное окружение... [Ожидайте]"
    python3 -m venv env
    if [ $? -ne 0 ]; then
        echo "[Ошибка] Не удалось создать виртуальное окружение."
        echo "Попробуйте: sudo apt install python3-venv"
        exit 1
    fi
fi

echo "Активация виртуального окружения..."
source env/bin/activate
if [ $? -ne 0 ]; then
    echo "[Ошибка] Не найдено виртуальное окружение."
    exit 1
fi

# ── Зависимости (сначала из локальной папки, потом из интернета) ───────────────
if [ -f "requirements.txt" ]; then
    if [ -d "packages" ]; then
        echo "Установка зависимостей из локальной папки packages/..."
        pip install -r requirements.txt --no-index --find-links packages/ -q
        if [ $? -ne 0 ]; then
            echo "[Внимание] Локальная установка не удалась, пробую через интернет..."
            pip install -r requirements.txt -q
            if [ $? -ne 0 ]; then
                echo "[Ошибка] Не удалось установить зависимости."
                deactivate
                exit 1
            fi
        fi
    else
        echo "Установка зависимостей из интернета..."
        pip install -r requirements.txt -q
        if [ $? -ne 0 ]; then
            echo "[Ошибка] Не удалось установить зависимости."
            deactivate
            exit 1
        fi
    fi
else
    echo "[Внимание] Файл requirements.txt не найден."
fi

# ── Миграции ───────────────────────────────────────────────────────────────────
echo "Применение миграций базы данных..."
python3 mykursovik2/manage.py migrate --run-syncdb -v 0
if [ $? -ne 0 ]; then
    echo "[Ошибка] Не удалось применить миграции."
    deactivate
    exit 1
fi

# ── Открыть браузер ────────────────────────────────────────────────────────────
(sleep 2 && xdg-open "http://127.0.0.1:8000" 2>/dev/null || open "http://127.0.0.1:8000" 2>/dev/null) &

# ── Запуск сервера ─────────────────────────────────────────────────────────────
echo "Запуск веб-приложения... Откройте http://127.0.0.1:8000"
python3 mykursovik2/manage.py runserver
if [ $? -ne 0 ]; then
    echo "[Ошибка] Не удалось запустить сервер Django."
    deactivate
    exit 1
fi

deactivate
