@echo off
setlocal
cd /d "%~dp0"

call :find_python
if defined PYTHON_CMD goto :install_requirements

echo.
echo Python is required to run this program.
choice /c YN /m "Install Python 3.13 now"
if errorlevel 2 goto :cancelled

where winget >nul 2>&1
if errorlevel 1 goto :winget_missing

echo.
echo Installing Python 3.13. Please wait...
winget install --exact --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :install_failed

call :find_python
if not defined PYTHON_CMD goto :python_not_found

:install_requirements
%PYTHON_CMD% -c "import PIL" >nul 2>&1
if not errorlevel 1 goto :run_app

echo.
echo Installing required library. Please wait...
%PYTHON_CMD% -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 goto :requirements_failed

:run_app
for /f "delims=" %%I in ('%PYTHON_CMD% -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%I"
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"

if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" "%~dp0photo_date_organizer.py"
) else (
    start "" %PYTHON_CMD% "%~dp0photo_date_organizer.py"
)
exit /b 0

:find_python
set "PYTHON_CMD="
py -3 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3"
if defined PYTHON_CMD exit /b 0
python -c "import sys" >nul 2>&1 && set "PYTHON_CMD=python"
exit /b 0

:winget_missing
echo.
echo WinGet is not available on this PC.
echo A browser will open. Install Python 3.13, then run this file again.
start "" "https://www.python.org/downloads/release/python-3130/"
pause
exit /b 1

:install_failed
echo.
echo Python installation did not complete. Please try again.
pause
exit /b 1

:python_not_found
echo.
echo Python was installed, but Windows cannot find it yet.
echo Close this window and run this file again.
pause
exit /b 1

:requirements_failed
echo.
echo The required library could not be installed. Check your internet connection and try again.
pause
exit /b 1

:cancelled
echo.
echo Python installation was cancelled.
pause
exit /b 0
