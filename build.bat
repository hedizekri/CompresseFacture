@echo off
echo === Compresseur de Factures - Build ===
echo.

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
echo Installation des dependances...
python -m pip install --only-binary :all: pymupdf Pillow pyinstaller

if %errorlevel% neq 0 (
    echo Tentative alternative...
    python -m pip install pymupdf Pillow pyinstaller
)

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
