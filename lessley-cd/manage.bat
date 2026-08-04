@echo off

:: 1. Check if the target argument is missing
if "%~1"=="" goto help

:: 2. Route based on the target (infra or app)
if /I "%~1"=="infra" goto infra
if /I "%~1"=="app" goto app
if /I "%~1"=="status" goto status

:: 3. Fallback if they type something wrong
goto help

:: ==========================================
:: GLOBAL COMMANDS
:: ==========================================
:status
echo [!] Checking status of ALL project containers...
docker compose ps
goto end

:: ==========================================
:: INFRASTRUCTURE COMMANDS
:: ==========================================
:infra
if /I "%~2"=="up" (
    echo [!] Starting infrastructure: RabbitMQ, Grafana, Loki, MongoDB, Mongo Express...
    docker compose up -d rabbitmq grafana loki mongodb mongo-express
    goto end
)

if /I "%~2"=="down" (
    if /I "%~3"=="-v" (
        echo [!] Stopping infrastructure AND removing volumes...
        docker compose rm -sfv rabbitmq grafana loki mongodb mongo-express
        goto end
    ) else (
        echo [!] Stopping infrastructure, keeping volumes safe...
        docker compose rm -sf rabbitmq grafana loki mongodb mongo-express
        goto end
    )
)

if /I "%~2"=="status" (
    echo [!] Checking infrastructure status...
    docker compose ps rabbitmq grafana loki mongodb mongo-express
    goto end
)

echo [X] Invalid action. Try: manage.bat infra up, manage.bat infra down, or manage.bat infra down -v or manage.bat infra status
goto end


:: ==========================================
:: APP COMMANDS (Lessley App)
:: ==========================================
:app
if /I "%~2"=="up" (
    echo [!] Starting Lessley core service: Personalization, Gateway, Deal Optimizer...
    docker compose up -d personalization gateway deal-optimizer
    goto end
)

if /I "%~2"=="build" (
    echo [!] Rebuilding and starting core service...
    docker compose up -d --build personalization gateway deal-optimizer
    goto end
)

if /I "%~2"=="down" (
    echo [!] Stopping core service...
    docker compose rm -sf personalization gateway deal-optimizer
    goto end
)

if /I "%~2"=="status" (
    echo [!] Checking core service status...
    docker compose ps personalization gateway deal-optimizer
    goto end
)

echo [X] Invalid action. Try: manage.bat app up, manage.bat app down, or manage.bat app status
goto end


:: ==========================================
:: HELP MENU
:: ==========================================
:help
echo [X] Invalid command or missing arguments.
echo.
echo Available commands:
echo   manage.bat status          - Shows the status of ALL containers
echo.
echo Infrastructure (RabbitMQ, Grafana, Loki, MongoDB):
echo   manage.bat infra up        - Starts infrastructure containers
echo   manage.bat infra down      - Removes containers (-v to wipe volumes)
echo   manage.bat infra status    - Shows status of infrastructure
echo.
echo Core Services (Personalization, Gateway, Deal Optimizer):
echo   manage.bat app up      - Starts application containers
echo   manage.bat app build   - Rebuilds code and starts containers
echo   manage.bat app down    - Removes application containers
echo   manage.bat app status  - Shows status of application containers
goto end


:: ==========================================
:: END OF SCRIPT
:: ==========================================
:end
echo [V] Done!