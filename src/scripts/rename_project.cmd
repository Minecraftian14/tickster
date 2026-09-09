@echo off

if "%1"=="--help" goto :help_message
if "%1"=="-h"     goto :help_message
if "%1"=="/?"     goto :help_message

set "kebab="
set "snake="
set "yes="
set "plan="

:arg_parse

    if "%~1"=="--yes"  set "yes=true"  & goto :continue_arg_parse
    if "%~1"=="-y"     set "yes=true"  & goto :continue_arg_parse
    if "%~1"=="--plan" set "plan=echo" & goto :continue_arg_parse
    if "%~1"=="-p"     set "plan=echo" & goto :continue_arg_parse

    if "%~2"=="" goto :skip_direct_naming
    if "%~1"=="--kebab" set "kebab=%~2" & shift & goto :continue_arg_parse
    if "%~1"=="-k"      set "kebab=%~2" & shift & goto :continue_arg_parse
    if "%~1"=="--snake" set "snake=%~2" & shift & goto :continue_arg_parse
    if "%~1"=="-s"      set "snake=%~2" & shift & goto :continue_arg_parse
    :skip_direct_naming

    if not "%kebab%%snake%"=="" echo Extra args provided from "%~1" & exit /b
    set "kebab=%~1"

    :continue_arg_parse
    shift
    if not "%~1"=="" goto :arg_parse


rem Verify whether either of kebab, snake are given.
if "%kebab%%snake%"=="" echo Please give a new name in kebab case & exit /b

rem Verify whether the given kebab name is valid.
set "short_kebab="
for /f "delims=" %%i in ('echo +%kebab% ^| tr -d -c a-z0-9-') do set "short_kebab=%%i"
if not "%kebab%"=="%short_kebab%" echo Invalid kebab name! & exit /b

rem Verify whether the given snake name is valid.
set "short_snake="
for /f "delims=" %%i in ('echo +%snake% ^| tr -d -c a-z0-9_') do set "short_snake=%%i"
if not "%snake%"=="%short_snake%" echo Invalid snake name! & exit /b

rem Derive the kebab or snake name from snake or kebab name respectively if not supplied.
if "%kebab%"=="" for /f "delims=" %%i in ('echo %snake%^| tr _ -') do set "kebab=%%i"
if "%snake%"=="" for /f "delims=" %%i in ('echo %kebab%^| tr - _') do set "snake=%%i"

if not "%yes%"=="" goto :ignore_name_confirmation
echo Please confirm the names:
echo   Kebab Name: "%kebab%"
echo   Snake Name: "%snake%"
choice /C yN /M "Do you want to proceed"
if errorlevel 2 exit /b
:ignore_name_confirmation
    
rem Replace all occurances of the template name in the source files.
for /f "delims=" %%i in ('grep -Erl --exclude-dir^={node_modules^,.venv^,build^,.git^,.gradle^,__pycache__} project[-_]template') do (
    call :replace_in_file %%i
)

rem Rename all folders with the template name in the source.
for /f "delims=" %%i in ('dir /s /b ^| grep -E project_template$') do (
    call :rename_folder %%i %snake%
)
for /f "delims=" %%i in ('dir /s /b ^| grep -E project-template$') do (
    call :rename_folder %%i %kebab%
)

goto :eof

:replace_in_file
    if "%1"=="" exit /b
    if "%1"=="src/scripts/rename_project.cmd" exit /b
    if not "%yes%"=="" goto :continue_replace

    echo About to replace template name in %1 at:
    grep -n --color=always project[-_]template %1
    choice /C yN /M "Do you want to proceed"
    if errorlevel 2 exit /b

    :continue_replace
    %plan% sed -i 's/project_template/%snake%/g' %1
    %plan% sed -i 's/project-template/%kebab%/g' %1
exit /b

:rename_folder
    if "%1"=="" exit /b
    if "%2"=="" exit /b
    if not "%yes%"=="" goto :continue_rename

    echo About to rename template name in path %1
    choice /C yN /M "Do you want to proceed"
    if errorlevel 2 exit /b

    :continue_rename
    set "directory_path=%1"
    %plan% git mv %1 %directory_path:~0,-16%%2
exit /b

:help_message
echo Usage:
echo   rename_project [options] [name]
echo.
echo Description:
echo   Renames project-template references throughout the project.
echo.
echo   Both kebab-case and snake_case names can be provided. If only one
echo   is provided, the other is automatically derived.
echo.
echo Options:
echo   -k, --kebab [name]
echo       Set the new name in kebab-case.
echo       Only lowercase letters, numbers, and '-' are allowed.
echo.
echo   -s, --snake [name]
echo       Set the new name in snake_case.
echo       Only lowercase letters, numbers, and '_' are allowed.
echo.
echo   -y, --yes
echo       Skip all confirmation prompts and proceed automatically.
echo.
echo   -p, --plan
echo       Show the commands that would be executed without making changes.
echo.
echo   -h, --help, /?
echo       Show this help message.
echo.
echo Name:
echo   A name can be provided directly without an option. This is treated as
echo   a kebab-case name.
echo.
echo   Examples:
echo     rename_project my-project
echo     rename_project --kebab my-project
echo     rename_project --snake my_project
echo     rename_project --kebab my-project --snake my_project
echo.
echo Behavior:
echo   - "project-template" references are replaced with the kebab-case name.
echo   - "project_template" references are replaced with the snake_case name.
echo   - Directories named "project-template" or "project_template" are renamed.
echo   - *The rename script itself is excluded from replacements.
echo   - Common dependency/build directories are excluded from the search.
