# Política de segurança

## Versões suportadas

Correções de segurança são priorizadas na versão estável mais recente do Lontrium. Releases antigas podem não receber correções individuais.

## Reportando uma vulnerabilidade

Não abra uma issue pública com senhas, cookies, chaves TOTP, tokens, capturas de rede ou logs completos.

Para reportar uma vulnerabilidade, use o recurso **Report a vulnerability** na aba **Security** do repositório. Se essa opção não estiver disponível, abra uma issue sem incluir dados sensíveis e escreva apenas `security report` no título; a triagem será feita de forma privada assim que possível.

Inclua, quando seguro:

- versão do Lontrium e sistema operacional;
- passos mínimos para reproduzir o problema;
- impacto observado;
- uma sugestão de correção, se já existir.

O Lontrium é uma aplicação local. Nunca envie seu banco de dados, volume do Docker ou perfil do navegador para investigação sem remover credenciais e sessões antes.
