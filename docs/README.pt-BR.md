<p align="center">
  <img src="images/lontrium-logo.png" alt="Lontrium Control" width="128" height="128">
</p>

<h1 align="center">Lontrium Control</h1>

<p align="center">
  <strong>Seus jogos gratuitos e recompensas diárias em um painel local e privado.</strong><br>
  Instale uma vez, escolha as lojas e deixe o Lontrium Control cuidar da rotina.
</p>

<p align="center">
  <a href="../LICENSE"><img alt="Licença AGPL-3.0" src="https://img.shields.io/github/license/rafaelcairess/lontrium?style=for-the-badge"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="Docker Compose" src="https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white">
</p>

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="./README.pt-BR.md">Português do Brasil</a> ·
  <a href="./README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/rafaelcairess/lontrium/releases/latest/download/Lontrium-Setup.exe"><strong>Baixar o Lontrium Control para Windows</strong></a>
</p>

> [!NOTE]
> **O Lontrium Control v1.3.0 já está disponível.** Baixe o instalador acima e confira o arquivo [`SHA256SUMS.txt`](https://github.com/rafaelcairess/lontrium/releases/latest/download/SHA256SUMS.txt).

<p align="center">
  <img src="images/05-dashboard.png" alt="Painel do Lontrium Control mostrando jogos e resultados do AliExpress e da Shopee" width="1100">
</p>

## O que ele faz

- Resgata jogos, recursos e recompensas elegíveis nas lojas selecionadas.
- Coleta moedas diárias do AliExpress e da Shopee e mostra o resultado e o saldo.
- Informa o resultado real de cada execução, não apenas uma contagem genérica.
- Executa por agendamento e pode iniciar automaticamente com o Windows.
- Abre um navegador visual quando uma loja exige login ou confirmação manual.
- Mantém painel, configurações, banco e sessões do navegador no seu computador.
- Guarda por 90 dias um histórico sanitizado que continua disponível após reinícios e atualizações.

## Serviços compatíveis

| Jogos e recursos | Recompensas e descoberta |
|---|---|
| Epic Games, Steam, GOG, Prime Gaming, Ubisoft, Fab e Unity Asset Store | Moedas diárias do AliExpress e da Shopee, além das promoções do GamerPower |

O GamerPower também pode encaminhar promoções compatíveis do Fanatical, itch.io e IndieGala. A disponibilidade e os requisitos de login dependem de cada loja.

> [!IMPORTANT]
> **A Shopee exige um primeiro login manual pela opção _Entrar com Google_.** No teste real, a segurança da Shopee bloqueou o login direto dentro do navegador Docker, mas o login pelo Google funcionou. O Lontrium não tenta contornar essa proteção; depois do acesso pelo Google, o perfil persistente local reutiliza a sessão.

## Instale em três passos

1. Baixe `Lontrium-Setup.exe` na [Release mais recente](https://github.com/rafaelcairess/lontrium/releases).
2. Execute o instalador. Se o Docker Desktop não estiver presente, o launcher explica por que ele é necessário e só instala pela fonte oficial após sua confirmação.
3. Siga o assistente local. Ele recomenda login pelo navegador, mostra apenas opções das lojas escolhidas e oferece rotinas simples de automação.

Pronto. Você não precisa clonar o repositório, editar arquivos de configuração ou digitar comandos Docker.

> [!TIP]
> **Você não precisa fornecer suas senhas ao Lontrium.** Em todas as lojas compatíveis que exigem conta, escolha o login pelo navegador e entre diretamente no site oficial. O Lontrium guarda a sessão resultante no volume Docker local e a reutiliza até que a própria loja solicite autenticação novamente.

O instalador pode solicitar permissão de administrador ou uma reinicialização durante a instalação do Docker Desktop. Como o primeiro instalador não será assinado, o Windows SmartScreen poderá mostrar um aviso de editor desconhecido. Cada Release inclui `SHA256SUMS.txt` para verificar o download.

## Primeira configuração

O assistente faz seis escolhas práticas, sem exigir que o usuário entenda variáveis de ambiente:

1. **Idioma** — detectado do Windows/navegador, com português, inglês e espanhol.
2. **Lojas** — somente as selecionadas aparecem no painel e participam das execuções.
3. **Login** — entrar pelo navegador é o modo recomendado; salvar credenciais localmente é opcional.
4. **Contas** — no login pelo navegador, nenhuma senha é solicitada. No outro modo, aparecem apenas os campos das lojas escolhidas.
5. **Automação** — escolha executar ao iniciar o Lontrium e diariamente, somente diariamente ou somente manual.
6. **Revisão** — confirma onde os dados ficam e explica o próximo passo.

Depois de **Concluir e executar**, o painel abre e inicia as lojas escolhidas. Quando alguma delas pedir autenticação, abra **Navegador** e faça o login no site oficial. O perfil persistente reutiliza essa sessão até que a própria loja a expire.

Você pode rever toda a introdução depois em **Configurações → Introdução**. Ela abre em modo de visualização e não sobrescreve configurações nem inicia uma execução.

## Como funciona

```text
Atalho do Windows → Docker Desktop → container local
                                      ├─ painel em 127.0.0.1:8080
                                      ├─ navegador visual em 127.0.0.1:7080
                                      ├─ módulos das lojas selecionadas
                                      └─ volume local persistente
                                         (configurações, sessões e histórico)
```

Cada módulo abre o site oficial, verifica a oferta ou recompensa e salva um resultado estruturado. Jogos mostram título e resultado; AliExpress e Shopee mostram moedas e os dados de saldo ou sequência disponibilizados pela página. CAPTCHA, antifraude e verificações de conta são devolvidos ao usuário no navegador visual e nunca são contornados. No Windows, um pequeno auxiliar nativo pode avisar quando um CAPTCHA exige atenção e abrir a sessão local do navegador com um clique.

## Seus dados ficam no seu computador

O Lontrium Control não possui servidor de contas e não inclui telemetria.

| O que acontece | Onde acontece |
|---|---|
| Painel e configurações | Em `127.0.0.1`, acessível somente neste computador |
| Credenciais e sessões | No volume Docker local |
| Histórico sanitizado de execuções | No banco SQLite local por 90 dias |
| Login nas lojas | Diretamente entre o navegador automatizado e o site oficial da loja |
| Resposta da API sobre segredos | Somente `configured: true/false`; a senha nunca retorna ao painel |
| Atualizações | Consultadas nas Releases oficiais deste projeto no GitHub |

As credenciais são opcionais e o login manual pelo navegador está sempre disponível. Os segredos locais não são protegidos por um servidor externo de criptografia; mantenha sua conta do Windows e o disco protegidos. O Lontrium Control não tenta contornar CAPTCHA, sistemas antifraude ou desafios de segurança.

## Feito para ser claro

Somente as lojas habilitadas aparecem no painel. Cada linha informa o que aconteceu: qual jogo foi resgatado, qual já estava na biblioteca, se não havia promoção ou quantas moedas do AliExpress ou da Shopee foram coletadas.

### Configuração guiada

<p align="center">
  <img src="images/04-credentials.png" alt="Campo de credencial com explicação de privacidade" width="1000">
</p>

### Detalhes das moedas do AliExpress

<p align="center">
  <img src="images/06-aliexpress.png" alt="Moedas diárias, saldo e sequência do AliExpress" width="1000">
</p>

O login pelo navegador é a opção recomendada, então o assistente não pede senhas sem uma escolha explícita. Cada credencial possui uma explicação acessível no botão `?`. A interface funciona com mouse, teclado e toque e está traduzida integralmente para inglês, português do Brasil e espanhol.

## Uso diário

- Abra o **Lontrium Control** pelo menu Iniciar ou pelo atalho da área de trabalho.
- Use **Executar agora** para todas as lojas ou execute somente uma delas.
- Use **Navegador** quando uma loja solicitar login, CAPTCHA ou confirmação manual.
- Ative **Notificações do Windows para ações manuais** para receber um único alerta local por CAPTCHA detectado. O auxiliar lê somente um evento sem segredos em `127.0.0.1`.
- Use **Configurações** para alterar lojas, contas, notificações e agendamento.
- As atualizações são oferecidas no painel e preservam o volume local.

Ao atualizar uma instalação antiga, o launcher pode perguntar se deve reutilizar contas e sessões existentes. Escolha **Sim**, a menos que queira começar com um perfil limpo. O container é substituído, mas o volume persistente selecionado é preservado.

O atalho normal verifica o Docker, inicia o serviço, espera o painel responder e o abre automaticamente. Para a inicialização com o Windows, o instalador oferece o modo econômico (padrão), que aguarda a coleta e libera a memória WSL do Docker, ou o modo painel, que mantém o painel local disponível. A desinstalação mantém contas e sessões por padrão; apagar os dados locais é uma opção separada e explícita. O Docker Desktop nunca é removido automaticamente.

## Precisa de ajuda?

| Problema | O que fazer |
|---|---|
| O painel não abriu | Abra [http://127.0.0.1:8080](http://127.0.0.1:8080) e confirme que o Docker Desktop está em execução. |
| Uma loja precisa de atenção | Abra o navegador visual pelo painel e conclua a solicitação oficial da loja. |
| Uma sessão expirou | Entre novamente pelo navegador visual; a sessão atualizada permanecerá local. |
| Um resgate falhou | Tente executar somente aquela loja e anexe o trecho relevante do log sanitizado ao abrir uma issue. |

Para relatar bugs ou sugerir recursos, use as [Issues do GitHub](https://github.com/rafaelcairess/lontrium/issues). Nunca publique senhas, cookies, chaves TOTP, capturas completas de rede ou imagens sem sanitização.

## Para contribuidores

O instalador é o caminho recomendado para usuários. Builds pelo código-fonte, arquitetura e variáveis internas são assuntos para desenvolvimento:

- [`.env.example`](../.env.example) — referência completa para builds pelo código-fonte
- [`MODIFICATIONS.md`](../MODIFICATIONS.md) — histórico da implementação e diferenças técnicas
- [`CHANGELOG.md`](../CHANGELOG.md) — mudanças de cada versão

A suíte cobre módulos das lojas, API local, proteção de segredos, traduções, configuração inicial e launcher do Windows.

## Créditos e licença

**Interface e distribuição Windows do Lontrium Control:** [Rafael Caires](https://github.com/rafaelcairess).

Construído sobre [P-Adamiec/Free-Games-Claimer-Remaster](https://github.com/P-Adamiec/Free-Games-Claimer-Remaster), mantido por Paweł Adamiec e seus contribuidores. Esse projeto foi inspirado em [vogler/free-games-claimer](https://github.com/vogler/free-games-claimer). Os avisos de terceiros estão em [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

Distribuído sob a [GNU Affero General Public License v3.0](../LICENSE).
