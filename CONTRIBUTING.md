# Contribuindo com o Lontrium

Obrigado pelo interesse. Issues, correções de documentação, testes e melhorias de módulos são bem-vindos.

## Antes de abrir um pull request

1. Explique o problema ou a decisão na issue relacionada.
2. Mantenha o pull request pequeno e focado.
3. Não inclua segredos, cookies, chaves TOTP, dados de contas ou logs não sanitizados.
4. Atualize testes e documentação quando o comportamento mudar.

## Verificações locais

```powershell
python -m pytest -q
node --check src/gui/static/app.js
node --test tests/test_i18n.js
```

Para alterações no instalador ou nos fluxos Windows, execute também as verificações específicas em `tests/installer.Tests.ps1` quando estiver em um ambiente Windows com os pré-requisitos instalados.

## Pull requests

Descreva o que mudou, como foi validado e qualquer limitação conhecida. Alterações de login devem respeitar CAPTCHA, antifraude, login social e confirmação manual: o Lontrium não tenta contornar esses mecanismos.
