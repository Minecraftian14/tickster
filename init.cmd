@echo off

if "%1"=="--help" goto :help_message
if "%1"=="-h"     goto :help_message
if "%1"=="/?"     goto :help_message

set "venv_finishing="

if exist .venv goto :skip_venv_creation
call uv venv || ( echo "Creating of Python Virtual Environment failed!" & exit /b )
set "venv_finishing=yes"
:skip_venv_creation

if exist node_modules goto :skip_node_modules_creation
call npm i || ( echo "Installation of Node Modules failed!" & exit /b )
:skip_node_modules_creation

call .venv\Scripts\activate || ( echo "Unable to activate Python Virtual Environment!" & exit /b )

if not "%venv_finishing%"=="yes" goto :skip_venv_finishing
call uv sync || ( echo "Python Virtual Environment sync failed!" & exit /b )
:skip_venv_finishing

set "PATH=%~dp0src\scripts;%PATH%"

if not exist .env call initialize_env -q -D

xonsh

exit /b


:help_message
echo.
echo This script sets up and starts the development environment.
echo.
echo The following steps are performed:
echo   1. Create the Python Virtual Environment if it does not exist.
echo   2. Install Node Modules if they are not already installed.
echo   3. Activate the Python Virtual Environment.
echo   4. Sync the Python Virtual Environment dependencies.
echo      This is only done when the Virtual Environment was newly created.
echo   5. Add the project's scripts directory to PATH.
echo   6. Initialize the .env file if it does not exist.
echo   7. Start xonsh.
echo.
echo Usage:
echo   init         Run the steps listed above
echo   init help    Print this message
echo.
echo Note:
echo   Run `rename_project help` to update the project name.
echo.
