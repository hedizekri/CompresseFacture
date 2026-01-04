@echo off
echo === Compresseur de Factures - Build ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe.
    echo Installez Python depuis https://www.python.org/downloads/
    echo IMPORTANT: Cochez "Add Python to PATH" lors de l'installation!
    pause
    exit /b 1
)

echo Python trouve. Installation des dependances...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install dependencies directly (no venv to avoid path issues)
python -m pip install pypdf==4.0.1 Pillow==10.1.0 pyinstaller==6.3.0

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Installation des dependances echouee.
    echo Essayez d'executer ce fichier en tant qu'administrateur.
    pause
    exit /b 1
)

echo.
echo Creation de l'executable...
python -m PyInstaller --onefile --windowed --name "CompresseurFactures" app.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Creation de l'executable echouee.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD TERMINE!
echo   L'executable est: dist\CompresseurFactures.exe
echo ============================================
echo.
pause
