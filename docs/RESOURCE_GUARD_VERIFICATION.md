# Verificação da proteção de recursos

Esta entrega adiciona uma verificação automática antes das execuções agendadas.

## Comportamento

- mede RAM, CPU, GPU e a janela em primeiro plano no Windows;
- não exige uma lista manual de jogos;
- não inicia o Docker quando a máquina está sob pressão;
- adia para o próximo horário configurado;
- no último horário do dia, executa sob pressão moderada;
- continua bloqueando quando a memória livre está em nível crítico;
- mostra uma notificação do Windows com o motivo e o próximo horário.

## Limites padrão

    RAM mínima livre: 3072 MB
    RAM crítica: 1024 MB
    CPU: 85%
    GPU: 80%

Os limites podem ser ajustados no arquivo .env com RESOURCE_*. Não é necessário
cadastrar jogos ou programas protegidos.

## Verificação local

Na raiz do repositório:

    .\.venv\Scripts\python.exe -m pytest -q
    dotnet build installer\windows-notifier\Lontrium.Notifier.csproj --configuration Release --nologo

O inicializador que verifica o host é installer/Start-ClaimerControl.ps1.
O monitor Python em src/core/resource_guard.py funciona como fallback para
execuções fora do inicializador Windows.

## Observação sobre o instalador

O Inno Setup (iscc.exe) não estava instalado nesta máquina. Por isso o
instalador .exe completo não foi regenerado; o notificador compilado está
incluído nesta pasta de verificação.
