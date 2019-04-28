@echo off
call:main %*
goto:eof

:usage
echo.############################################################
echo.
echo.Use `./provision.bat` to interact with Yombo.
echo.
echo.Examples:
echo.
echo.- setup the environment: `./provision.bat start`
echo.- restart Yombo process: `./provision.bat restart`
echo.- destroy the host and start anew: `./provision.bat recreate`
echo.
echo.See https://yombo.net/docs/gateway/vagrant for more details.
echo.
echo.############################################################'
goto:eof

:main
if "%*"=="setup" (
    if exist setup_done del setup_done
    vagrant up --provision
    copy /y nul setup_done
) else (
if "%*"=="restart" (
    copy /y nul restart
    vagrant provision
) else (
if "%*"=="start" (
    vagrant resume
) else (
if "%*"=="stop" (
    vagrant halt
) else (
if "%*"=="destroy" (
    vagrant destroy -f
) else (
if "%*"=="recreate" (
    if exist setup_done del setup_done
    if exist restart del restart
    vagrant destroy -f
    vagrant up --provision
) else (
    call:usage
))))))