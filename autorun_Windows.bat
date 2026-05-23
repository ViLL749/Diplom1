@echo off
chcp 65001 >nul
title APM Avtosservis

REM -----------------------------------------------------------------------
REM  Proverka Python
REM -----------------------------------------------------------------------
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [Oshibka] Python ne nayden. Ustanovite Python 3.10+ s https://python.org
    pause
    exit /b 1
)

REM -----------------------------------------------------------------------
REM  Virtualnoe okruzhenie
REM -----------------------------------------------------------------------
if not exist env (
    echo Sozdayu virtualnoe okruzhenie... Podozhdite.
    py -m venv env
    if %errorlevel% neq 0 (
        echo [Oshibka] Ne udalos sozdat virtualnoe okruzhenie.
        pause
        exit /b 1
    )
)

echo Aktivatsiya virtualnogo okruzheniya...
call env\Scripts\activate
if %errorlevel% neq 0 (
    echo [Oshibka] Ne udalos aktivirovat virtualnoe okruzhenie.
    pause
    exit /b 1
)

REM -----------------------------------------------------------------------
REM  Zavisimosti
REM -----------------------------------------------------------------------
if exist requirements.txt (
    echo Ustanovka zavisimostey... Podozhdite.
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [Oshibka] Ne udalos ustanovit zavisimosti.
        pause
        exit /b 1
    )
) else (
    echo [Vnimanie] Fayl requirements.txt ne nayden.
)

REM -----------------------------------------------------------------------
REM  Migratsii
REM -----------------------------------------------------------------------
echo Primeneniye migratsiy bazy dannykh...
py mykursovik2\manage.py migrate --run-syncdb -v 0
if %errorlevel% neq 0 (
    echo [Oshibka] Ne udalos primenit migratsii.
    pause
    exit /b 1
)

REM -----------------------------------------------------------------------
REM  Otkryt brauzer cherez 2 sekundy
REM -----------------------------------------------------------------------
echo Zapusk veb-prilozheniya...
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"

REM -----------------------------------------------------------------------
REM  Zapusk servera
REM -----------------------------------------------------------------------
py mykursovik2\manage.py runserver
if %errorlevel% neq 0 (
    echo [Oshibka] Ne udalos zapustit server Django.
    pause
    exit /b 1
)

pause
