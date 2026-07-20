
@echo off
echo Installing PyInstaller if needed...
python -m pip install pyinstaller
echo.
echo Building BeltCalculator.exe...
pyinstaller --onefile --windowed --name BeltCalculator belt_calculator_gui.pyw
echo.
echo Done. Check the dist folder for BeltCalculator.exe
pause
