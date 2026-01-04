@echo off
echo === Compresseur de Factures - Build ===
echo.

REM Check Python version
python --version
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas trouve.
    pause
    exit /b 1
)

echo.
echo Mise a jour de pip...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Installation de Pillow (binaire pre-compile)...
python -m pip install --only-binary :all: Pillow

if %errorlevel% neq 0 (
    echo.
    echo Tentative alternative...
    python -m pip install Pillow --prefer-binary
)

echo.
echo Installation des autres dependances...
python -m pip install pypdf pyinstaller

echo.
echo Creation de l'executable...
python -m PyInstaller --onefile --windowed --name "CompresseurFactures" app.py

if exist "dist\CompresseurFactures.exe" (
    echo.
    echo ============================================
    echo   BUILD TERMINE!
    echo   L'executable est: dist\CompresseurFactures.exe
    echo ============================================
) else (
    echo.
    echo ERREUR: L'executable n'a pas ete cree.
)

echo.
pause
