<p align="center">
  <img src="docs/images/lontrium-logo.png" alt="Lontrium Control" width="116">
</p>

<h1 align="center">Lontrium Control</h1>

<p align="center">
  <strong>Automação local para jogos grátis, recompensas diárias e ofertas digitais.</strong><br>
  Escolha as lojas. O Lontrium cuida da rotina sem tirar suas credenciais do computador.
</p>

<p align="center">
  <a href="https://github.com/rafaelcairess/lontrium/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/rafaelcairess/lontrium?style=flat-square&label=release"></a>
  <a href="https://github.com/rafaelcairess/lontrium/actions/workflows/release.yml"><img alt="Build and release" src="https://img.shields.io/github/actions/workflow/status/rafaelcairess/lontrium/release.yml?style=flat-square&label=build"></a>
  <a href="./LICENSE"><img alt="AGPL-3.0 license" src="https://img.shields.io/github/license/rafaelcairess/lontrium?style=flat-square"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white">
</p>

<p align="center">
  <a href="https://github.com/rafaelcairess/lontrium/releases/latest/download/Lontrium-Setup.exe"><strong>Baixar para Windows</strong></a>
  ·
  <a href="#como-funciona">Como funciona</a>
  ·
  <a href="#para-desenvolvedores">Para desenvolvedores</a>
</p>

<p align="center">
  <a href="./README.md">README principal</a> ·
  <a href="./docs/README.pt-BR.md">Português do Brasil</a> ·
  <a href="./docs/README.es.md">Español</a>
</p>

<p align="center">
  <img src="docs/images/01-dashboard.png" alt="Dashboard do Lontrium mostrando lojas ativas, automação e privacidade local" width="1000">
</p>

> [!NOTE]
> A versão estável atual é a **v1.7.1**. O instalador e o arquivo `SHA256SUMS.txt` estão na [última release](https://github.com/rafaelcairess/lontrium/releases/latest).

## Em poucas palavras

O Lontrium é um aplicativo local para Windows que reúne tarefas repetitivas de lojas digitais em um único painel. Ele abre os sites oficiais em um navegador visual, reutiliza sessões persistentes, registra o resultado de cada execução e agenda novas tentativas quando uma loja precisa de atenção.

O projeto nasceu de um problema simples: ofertas e recompensas expiram enquanto o usuário está trabalhando, jogando ou longe do computador. A proposta é automatizar o trabalho mecânico sem transformar senhas, cookies ou histórico em dados de um servidor externo.

## O que ele faz

| Área | Experiência do usuário |
| --- | --- |
| Jogos e ofertas | Verifica jogos grátis, ativos e ofertas elegíveis nas lojas selecionadas. |
| Recompensas | Coleta recompensas diárias do AliExpress e da Shopee quando a sessão está disponível. |
| Agendamento | Executa nos horários escolhidos e retoma tarefas pendentes sem repetir o que já foi concluído no dia. |
| Login | Prioriza login manual no navegador; credenciais salvas são apenas um recurso opcional de preenchimento. |
| Segurança operacional | Nunca tenta contornar CAPTCHA, antifraude, login Google ou códigos de verificação. |
| Uso do computador | Avalia RAM, CPU, GPU e aplicativos pesados antes de iniciar uma execução agendada. Se o computador estiver ocupado, adia para o próximo horário configurado. |
| Privacidade | Dashboard, configurações, banco local e sessões do navegador permanecem no computador do usuário. |

## Lojas suportadas

O usuário escolhe quais módulos quer habilitar. Apenas as lojas selecionadas aparecem no dashboard e nas configurações.

| Loja ou módulo | O que é automatizado | Login |
| --- | --- | --- |
| Epic Games | Jogos grátis e ofertas elegíveis | Navegador ou credenciais opcionais |
| GOG | Giveaways atuais | Navegador ou credenciais opcionais |
| Prime Gaming | Ofertas e resgates compatíveis | Navegador ou credenciais opcionais |
| Steam, Ubisoft, Fab e Unity | Ofertas e ativos disponíveis no fluxo da loja | Conforme a loja |
| AliExpress | Check-in, moedas, saldo e sequência | Navegador ou credenciais opcionais |
| Shopee | Check-in e saldo | **Login manual no navegador** |
| GamerPower | Descoberta de giveaways e fontes parceiras | Depende do destino |

O GamerPower pode usar fontes opcionais como Fanatical, itch.io e IndieGala. O Fab reutiliza a sessão da Epic e não exige credenciais próprias.

> [!IMPORTANT]
> Para o Shopee, use **Continue with Google** no navegador visual. Essa é a forma recomendada pelo Lontrium porque o login direto pode ser recusado pelos mecanismos de segurança da loja.

## Instalação rápida

1. Baixe [`Lontrium-Setup.exe`](https://github.com/rafaelcairess/lontrium/releases/latest/download/Lontrium-Setup.exe) na release mais recente.
2. Execute o instalador. Se necessário, ele explica a instalação do Docker Desktop e pede confirmação antes de prosseguir.
3. Siga o assistente, selecione as lojas e faça o login no navegador visual quando solicitado.

Depois disso, abra o Lontrium pelo menu Iniciar ou pelo atalho criado na área de trabalho. Não é necessário clonar o repositório, editar arquivos `.env` ou digitar comandos Docker para usar a versão distribuída.

> [!TIP]
> Você não precisa entregar suas senhas ao Lontrium. O login pelo navegador é o caminho recomendado: a sessão fica no perfil local e é reutilizada até a loja pedir uma nova autenticação.

## Como funciona

```text
Agendador do Windows
        │
        ├── verifica se o computador está disponível
        ├── adia a execução se houver jogo ou carga alta
        ├── inicia Docker somente quando necessário
        ├── executa apenas lojas pendentes no dia
        └── encerra os recursos que ele próprio iniciou
                │
                ├── Dashboard local:  http://127.0.0.1:8080
                ├── Navegador visual:  http://127.0.0.1:7080
                └── Volume persistente:
                      ├── configurações e credenciais opcionais
                      ├── perfil de navegador por loja
                      └── histórico sanitizado de 90 dias
```

Cada módulo acessa o site oficial, interpreta o resultado e salva um resumo estruturado. CAPTCHA, antifraude, login social e confirmação por código continuam sob controle do usuário no navegador visual.

## Privacidade e segurança

| Dado | Onde fica |
| --- | --- |
| Dashboard e configurações | Computador local, em `127.0.0.1` |
| Sessões do navegador | Volume local do Docker |
| Histórico de execuções | Banco SQLite local, limitado a 90 dias |
| Segredos da API | O frontend recebe apenas se estão configurados, nunca o valor |
| Comunicação com lojas | Navegador automatizado acessando os sites oficiais |

O Lontrium não possui servidor de contas nem telemetria própria. A segurança do perfil local depende da conta do Windows e do disco do usuário. Consulte [`SECURITY.md`](./SECURITY.md) para reportar vulnerabilidades.

## Interface

O painel foi pensado para responder rapidamente a três perguntas: o que está ativo, o que aconteceu e o que precisa de atenção.

<table>
  <tr>
    <td width="50%" valign="top">
      <p align="center"><strong>Ajuda e login</strong></p>
      <img src="docs/images/02-help.png" alt="Área de ajuda do Lontrium explicando sessões e credenciais opcionais" width="100%">
    </td>
    <td width="50%" valign="top">
      <p align="center"><strong>Lojas selecionadas</strong></p>
      <img src="docs/images/03-stores.png" alt="Configurações de lojas do Lontrium" width="100%">
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <p align="center"><strong>Agendamento</strong></p>
      <img src="docs/images/04-schedule.png" alt="Configurações de agendamento do Lontrium" width="100%">
    </td>
    <td width="50%" valign="top">
      <p align="center"><strong>Notificações</strong></p>
      <img src="docs/images/06-notifications.png" alt="Configurações de notificações do Lontrium" width="100%">
    </td>
  </tr>
</table>

## Para desenvolvedores

O instalador é o caminho recomendado para usuários finais. Para executar a aplicação a partir do código-fonte, consulte [`MODIFICATIONS.md`](./MODIFICATIONS.md) e [`.env.example`](./.env.example).

### Stack

- **Python 3.11+** para API, módulos de lojas e automação.
- **Playwright** para os fluxos de navegador visual e sessões persistentes.
- **Docker Compose** para isolar a aplicação e seus serviços locais.
- **JavaScript, HTML e CSS** para o dashboard, configurações e onboarding.
- **GitHub Actions** para testes, build da imagem e publicação do instalador Windows.

### Qualidade

```powershell
python -m pytest -q
node --check src/gui/static/app.js
node --test tests/test_i18n.js
```

O conjunto de testes cobre módulos de loja, API local, fluxo de configuração, traduções, proteção de segredos, launcher Windows e comportamento do agendamento.

Para contribuir, abra uma issue descrevendo o problema ou envie um pull request pequeno e reproduzível. Nunca inclua senhas, cookies, chaves TOTP ou logs não sanitizados.

## Documentação

- [Guia em português](./docs/README.pt-BR.md)
- [Guia para colaboradores](./CONTRIBUTING.md)
- [Política de segurança](./SECURITY.md)
- [Guía en español](./docs/README.es.md)
- [Histórico de alterações](./CHANGELOG.md)
- [Verificação da proteção de recursos](./docs/RESOURCE_GUARD_VERIFICATION.md)
- [Notas de terceiros](./THIRD_PARTY_NOTICES.md)

## Créditos e licença

**Lontrium Control e distribuição para Windows:** [Rafael Caires](https://github.com/rafaelcairess).

O projeto foi construído a partir do [Free-Games-Claimer-Remaster](https://github.com/P-Adamiec/Free-Games-Claimer-Remaster), mantido por Paweł Adamiec e colaboradores, e inspirado no [free-games-claimer](https://github.com/vogler/free-games-claimer).

Distribuído sob a [GNU Affero General Public License v3.0](./LICENSE).

Se o Lontrium for útil para você, uma ⭐ no GitHub ajuda o projeto a alcançar mais pessoas.
