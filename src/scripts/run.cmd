@echo off

if "%1"=="--help" goto :help_message
if "%1"=="-h"     goto :help_message
if "%1"=="/?"     goto :help_message

set "call="
set "source="
set "flag="
set "state=prog"
set "tool_args="
set "prog_args="

:arg_parse

    if not "%flag%"=="source" goto :skip_source
    if "%~1"=="frontend" set "source=frontend" & set "flag=" & goto :continue
    if "%~1"=="fe"       set "source=frontend" & set "flag=" & goto :continue
    if "%~1"=="devtools" set "source=devtools" & set "flag=" & goto :continue
    if "%~1"=="dt"       set "source=devtools" & set "flag=" & goto :continue
    if "%~1"=="business" set "source=business" & set "flag=" & goto :continue
    if "%~1"=="bl"       set "source=business" & set "flag=" & goto :continue
    if "%~1"=="upstox"   set "source=upstox"   & set "flag=" & goto :continue
    if "%~1"=="us"       set "source=upstox"   & set "flag=" & goto :continue
    echo Unknown source name "%~1" & exit /b
    :skip_source

    if "%~1"=="--source"       set "flag=source" & goto :continue
    if "%~1"=="-s"             set "flag=source" & goto :continue
    if "%~1"=="--dry-run"      set "call=echo"   & goto :continue
    if "%~1"=="-d"             set "call=echo"   & goto :continue
    if "%~1"=="--tool-args"    set "state=tool"  & goto :continue
    if "%~1"=="-t"             set "state=tool"  & goto :continue
    if "%~1"=="--program-args" set "state=prog"  & goto :continue
    if "%~1"=="-p"             set "state=prog"  & goto :continue

    if "%state%"=="tool" set "tool_args=%tool_args% %1" & goto :continue
    if "%state%"=="prog" set "prog_args=%prog_args% %1" & goto :continue

    :continue
    shift
    if not "%~1"=="" goto :arg_parse


if "%source%"=="" echo Please specify the source name to run & exit /b
if "%source%"=="frontend" goto :run_frontend
if "%source%"=="devtools" goto :run_devtools
if "%source%"=="business" goto :run_business
if "%source%"=="upstox"   goto :run_upstox

:run_frontend
rem if not "%prog_args%"=="" set "prog_args=--%prog_args%"
%call% npm run dev %tool_args% -- --clearScreen false %prog_args%
exit /b

:run_devtools
if not "%prog_args%"=="" set "prog_args=--args="%prog_args:~1%""
%call% gradlew run %tool_args% %prog_args%
exit /b

:run_business
%call% uv run %tool_args% -m tickster %prog_args%
exit /b

:run_upstox
%call% uv run %tool_args% -m upstox_connector %prog_args%
exit /b

:help_message
echo Usage:
echo   run_project [options]
echo.
echo Description:
echo   Runs one of the project's applications or development tools.
echo.
echo Options:
echo   -s, --source SOURCE
echo       Select what to run.
echo.
echo       Available sources:
echo         frontend, fe
echo         devtools, dt
echo         business, bl
echo.
echo   -d, --dry-run
echo       Show the command that would be executed without running it.
echo.
echo   -t, --tool-args
echo       Treat all following arguments as arguments for the underlying tool.
echo.
echo   -p, --program-args
echo       Treat all following arguments as arguments for the program.
echo       This is the default.
echo.
echo   -h, --help, /?
echo       Show this help message.
echo.
echo Argument Handling:
echo   Arguments are passed to the selected tool or program.
echo.
echo   By default, arguments are passed to the program. Use --tool-args
echo   to switch to passing arguments to the underlying tool.
