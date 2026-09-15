@echo off
echo ===================================================
echo   Lontrium Control - Atualizacao de Dev (Local)
echo ===================================================
echo.

echo [1/3] Construindo a nova imagem Docker (ghcr.io/rafaelcairess/lontrium:local-stop-preview)...
cd /d "%~dp0"
docker build -t ghcr.io/rafaelcairess/lontrium:local-stop-preview .
if %errorlevel% neq 0 (
    echo.
    echo Falha ao construir a imagem Docker.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Copiando arquivos atualizados do instalador para a instalacao local...
copy /Y "installer\Start-ClaimerControl.ps1" "D:\Projetos\Claimer Control\"
copy /Y "installer\Start-ClaimerControl.cmd" "D:\Projetos\Claimer Control\"
copy /Y "installer\docker-compose.yml" "D:\Projetos\Claimer Control\"

echo.
echo [3/3] Atualizacao concluida com sucesso!
echo Reiniciando o Lontrium Control...
cd /d "D:\Projetos\Claimer Control\"
start "" "Start-ClaimerControl.cmd"

echo.
echo Pode fechar esta janela.
pause
