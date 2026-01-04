@echo off
echo === Compresseur de Factures - Build ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe.
    echo Installez Python depuis https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installation des dependances...
pip install -r requirements.txt

REM Build exe
echo.
echo Creation de l'executable...
pyinstaller --onefile --windowed --name "CompresseurFactures" app.py

echo.
echo ============================================
echo   BUILD TERMINE!
echo   L'executable est: dist\CompresseurFactures.exe
echo   Copiez ce fichier sur n'importe quel PC Windows.
echo ============================================
echo.
pause
