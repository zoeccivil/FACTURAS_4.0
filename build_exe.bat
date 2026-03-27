@echo off
REM ===================================================================
REM build_exe.bat
REM
REM Script para generar gestion_facturas.exe de forma automática
REM usando PyInstaller.
REM
REM Requisitos previos:
REM   1) Tener Python instalado y accesible en PATH (python o py).
REM   2) Tener un entorno virtual (opcional pero recomendado).
REM   3) Tener el archivo principal de la app:
REM        launch_modern_gui.py
REM
REM Este script:
REM   - Verifica Python
REM   - Instala/actualiza PyInstaller en el entorno actual
REM   - Empaqueta la app en un único EXE: gestion_facturas.exe
REM   - Coloca el EXE en la carpeta "dist"
REM ===================================================================

SETLOCAL ENABLEDELAYEDEXPANSION

REM ---------------------------------------------------------------
REM 1) Detectar comando de Python
REM ---------------------------------------------------------------
where python >NUL 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET PYTHON_CMD=python
) ELSE (
    where py >NUL 2>&1
    IF %ERRORLEVEL% EQU 0 (
        SET PYTHON_CMD=py
    ) ELSE (
        echo [ERROR] No se encontró Python en el PATH. Instala Python o agrega 'python' o 'py' al PATH.
        pause
        EXIT /B 1
    )
)

echo Usando: %PYTHON_CMD%

REM ---------------------------------------------------------------
REM 2) Definir nombre del script principal y del EXE
REM ---------------------------------------------------------------
SET MAIN_SCRIPT=launch_modern_gui.py

REM Nombre del ejecutable final
SET EXE_NAME=gestion_facturas.exe

REM ---------------------------------------------------------------
REM 3) Verificar que el script principal existe
REM ---------------------------------------------------------------
IF NOT EXIST "%MAIN_SCRIPT%" (
    echo [ERROR] No se encontró el archivo principal "%MAIN_SCRIPT%".
    echo Asegúrate de que este .bat esté en la misma carpeta que %MAIN_SCRIPT%
    echo o ajusta la variable MAIN_SCRIPT en este archivo.
    pause
    EXIT /B 1
)

REM ---------------------------------------------------------------
REM 4) Instalar / actualizar PyInstaller en el entorno actual
REM ---------------------------------------------------------------
echo.
echo Instalando / actualizando PyInstaller...
%PYTHON_CMD% -m pip install --upgrade pip >NUL 2>&1
%PYTHON_CMD% -m pip install --upgrade pyinstaller >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] No se pudo instalar/actualizar PyInstaller.
    pause
    EXIT /B 1
)

REM ---------------------------------------------------------------
REM 5) Limpiar builds anteriores
REM ---------------------------------------------------------------
echo.
echo Limpiando builds anteriores...
IF EXIST build (
    rmdir /S /Q build
)
IF EXIST dist (
    rmdir /S /Q dist
)

REM ---------------------------------------------------------------
REM 6) Ejecutar PyInstaller
REM ---------------------------------------------------------------
echo.
echo Empaquetando la aplicacion en %EXE_NAME% ...
echo (esto puede tardar varios minutos)

REM Opciones utilizadas:
REM   --onefile       : un solo .exe
REM   --noconsole     : sin consola de texto (solo interfaz gráfica)
REM   --name          : nombre del ejecutable final (sin .exe)
REM   --clean         : limpia cachés de PyInstaller
REM
REM Si tu app usa icono, descomenta y ajusta:
REM   --icon=icono.ico

%PYTHON_CMD% -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "%EXE_NAME:~0,-4%" ^
    --clean ^
    "%MAIN_SCRIPT%"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Fallo la construccion del ejecutable.
    pause
    EXIT /B 1
)

REM ---------------------------------------------------------------
REM 7) Mostrar resultado
REM ---------------------------------------------------------------
echo.
echo =============================================================
echo  Proceso completado.
echo  Ejecutable generado:
echo      dist\%EXE_NAME%
echo =============================================================
echo.
pause
ENDLOCAL