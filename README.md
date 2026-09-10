<p align="center">
  <img src="docs/images/lontrium-logo.png" alt="Lontrium Control" width="128" height="128">
</p>

<h1 align="center">Lontrium Control</h1>

<p align="center">
  <strong>Your free-game claims and daily rewards, organized in one private local dashboard.</strong><br>
  Install once, choose your stores, and let Lontrium Control handle the routine.
</p>

<p align="center">
  <a href="./LICENSE"><img alt="License AGPL-3.0" src="https://img.shields.io/github/license/rafaelcairess/lontrium?style=for-the-badge"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="Docker Compose" src="https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white">
</p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./docs/README.pt-BR.md">Português do Brasil</a> ·
  <a href="./docs/README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/rafaelcairess/lontrium/releases/latest/download/Lontrium-Setup.exe"><strong>Download Lontrium Control for Windows</strong></a>
</p>

> [!NOTE]
> **Lontrium Control v1.2.1 is available now.** Download the installer above and verify it with [`SHA256SUMS.txt`](https://github.com/rafaelcairess/lontrium/releases/latest/download/SHA256SUMS.txt).

<p align="center">
  <img src="docs/images/05-dashboard.png" alt="Lontrium Control dashboard showing game, AliExpress and Shopee results" width="1100">
</p>

## What it does

- Claims eligible free games, assets and rewards from your selected stores.
- Collects daily coin rewards from AliExpress and Shopee and shows the result and balance.
- Shows the actual result of each run instead of only a generic success count.
- Runs on a schedule and can start automatically with Windows.
- Opens a visual browser whenever a store requires manual login or confirmation.
- Keeps the dashboard, settings, database and browser sessions on your computer.
- Preserves a privacy-safe 90-day activity history across container restarts and app updates.
- Lets each store run independently, so a login wait in one store does not hide the controls for another supported independent run.

## Supported services

| Service | What Lontrium checks | First login |
|---|---|---|
| Epic Games | Free PC games and eligible Android/iOS offers | Saved credentials or visual browser |
| GOG | Current giveaways | Saved credentials or visual browser |
| Prime Gaming | Included games and supported redemption flows | Saved credentials or visual browser |
| Steam, Ubisoft, Fab and Unity | Supported free offers and assets | Depends on the store flow |
| AliExpress | Daily coin check-in, reward, balance and streak | Saved credentials or visual browser |
| Shopee | Daily coin check-in and balance | **Visual browser with Continue with Google** |
| GamerPower | Giveaway discovery and compatible partner claims | Depends on the destination store |

GamerPower can route compatible giveaways from Fanatical, itch.io and IndieGala. Store availability, regional offers and authentication requirements are controlled by each official service.

> [!IMPORTANT]
> **Shopee requires a one-time manual login through _Continue with Google_.** In our live test, Shopee's security rejected direct account login inside the Docker browser, while Google login succeeded. Lontrium does not attempt to bypass that protection; after the Google login, the local persistent browser profile reuses the session.

## Install in three steps

1. Download `Lontrium-Setup.exe` from the [latest Release](https://github.com/rafaelcairess/lontrium/releases).
2. Run it. If Docker Desktop is missing, the launcher explains why it is needed and installs it from Docker's official source only after your confirmation.
3. Follow the local setup assistant. It recommends browser login, shows only settings relevant to your selected stores and offers simple automation presets.

That is all. You do not need to clone the repository, edit configuration files or type Docker commands.

> [!TIP]
> **You do not have to give Lontrium your passwords.** For every supported store that requires an account, choose browser login and sign in directly on the official website. Lontrium keeps the resulting browser session in the local Docker volume and reuses it until that store asks you to authenticate again.

The installer may request administrator permission or a Windows restart while Docker Desktop is installed. Because the first installer is unsigned, Windows SmartScreen may display an unknown-publisher warning. Every Release includes `SHA256SUMS.txt` so the download can be verified.

## First-time setup

The assistant asks six practical questions instead of exposing the full environment configuration:

1. **Language** — automatically detected from Windows/browser; English, Brazilian Portuguese and Spanish are available.
2. **Stores** — only selected stores appear on the dashboard or participate in scheduled runs.
3. **Login method** — browser login is recommended; saving supported credentials locally remains optional.
4. **Accounts** — when browser login is selected, no password is requested. Otherwise, only fields for selected stores are shown.
5. **Automation** — choose a run when Lontrium starts plus a daily time, daily only, or manual only. Advanced intervals remain in Settings.
6. **Review** — confirms where data stays and explains exactly what will happen after finishing.

After **Finish and run**, Lontrium opens the dashboard and starts the selected services. If a store needs authentication, open **Browser**, finish the login on the official page and return to the dashboard. The browser profile is persistent, so this is normally required only on first use or after the store expires its own session.

You can revisit the complete introduction later from **Settings → Introduction**. It opens in preview mode and does not overwrite settings or start a run.

## How it works

```text
Windows shortcut
      │
      ├─ checks/starts Docker Desktop
      ├─ pulls the selected Lontrium image
      └─ starts the local container
                 │
                 ├─ dashboard → http://127.0.0.1:8080
                 ├─ visual browser → http://127.0.0.1:7080
                 ├─ scheduler → runs only enabled stores
                 └─ local volume
                       ├─ settings and optional credentials
                       ├─ separate browser profile per store
                       └─ sanitized 90-day result history
```

Each store module opens the corresponding official website, checks the current offer or reward and records a structured result. Games show their titles and outcomes. AliExpress and Shopee show collected coins and any balance/streak information the official page exposes. CAPTCHA, anti-fraud and account verification are handed back to the user in the visual browser; Lontrium never attempts to bypass them.

## Your data stays local

Lontrium Control has no account server and includes no telemetry.

| What happens | Where it happens |
|---|---|
| Dashboard and settings | On `127.0.0.1`, available only from this computer |
| Credentials and browser sessions | In the local Docker volume |
| Sanitized run history | In the local SQLite database for 90 days |
| Store login | Directly between the automated browser and the store's official website |
| Saved secret API response | Only `configured: true/false`; the password is never sent back to the dashboard |
| Updates | Checked against this project's official GitHub Releases |

Credentials are optional; manual browser login is always available. Locally saved secrets are not protected by an external encryption server, so your Windows account and disk must remain secure. Lontrium Control never attempts to bypass CAPTCHA, anti-fraud or security challenges.

## Designed for clarity

Only enabled stores appear on the dashboard. Each row reports what happened: which game was claimed, which one was already owned, whether no giveaway was available, or how many AliExpress or Shopee coins were collected.

### Guided setup

<p align="center">
  <img src="docs/images/04-credentials.png" alt="Credential field with its privacy explanation" width="1000">
</p>

### AliExpress coin details

<p align="center">
  <img src="docs/images/06-aliexpress.png" alt="AliExpress daily coins, balance and streak" width="1000">
</p>

Browser login is the recommended default, so the assistant does not request passwords unless the user explicitly selects local credential storage. Every credential field includes an accessible `?` explanation. The interface supports mouse, keyboard and touch, and is fully translated into English, Brazilian Portuguese and Spanish.

## Daily use

- Open **Lontrium Control** from the Start menu or desktop shortcut.
- Use **Run now** for all enabled stores or run one store individually.
- Use **Browser** when a store asks for login, CAPTCHA or manual confirmation.
- Use **Settings** to change stores, accounts, notifications or scheduling.
- Updates are offered in the dashboard and preserve the local volume.

When upgrading from the older Free Games Claimer layout, the launcher may ask whether it should reuse existing local accounts and sessions. Choose **Yes** unless you intentionally want a clean profile. Lontrium changes the container and application image, not the selected persistent data volume.

The normal Windows shortcut checks Docker, starts the service, waits for the dashboard and opens it automatically. For Windows sign-in, the installer offers economy mode (the default), which waits for the claim run and releases Docker's WSL memory, or dashboard mode, which keeps the local panel available. Uninstalling Lontrium Control keeps accounts and sessions by default; deleting local data is a separate, explicit option. Docker Desktop is never removed automatically.

## Need help?

| Problem | What to try |
|---|---|
| Dashboard did not open | Open [http://127.0.0.1:8080](http://127.0.0.1:8080) and confirm Docker Desktop is running. |
| A store needs attention | Open the visual browser from the dashboard and complete the official store prompt. |
| A session expired | Sign in again through the visual browser; the refreshed session is kept locally. |
| A claim failed | Retry the individual store and include the relevant sanitized log when opening an issue. |

For bugs and feature requests, use [GitHub Issues](https://github.com/rafaelcairess/lontrium/issues). Never publish passwords, cookies, TOTP keys, complete network captures or unsanitized screenshots.

## For contributors

The installer is the supported path for end users. Source builds, architecture and environment variables are developer-facing topics:

- [`.env.example`](./.env.example) — complete source-build configuration reference
- [`MODIFICATIONS.md`](./MODIFICATIONS.md) — implementation history and technical differences
- [`CHANGELOG.md`](./CHANGELOG.md) — release changes

The test suite covers store logic, the local API, secret handling, translations, setup flow and the Windows launcher.

## Credits and license

**Lontrium Control interface and Windows distribution:** [Rafael Caires](https://github.com/rafaelcairess).

Built on [P-Adamiec/Free-Games-Claimer-Remaster](https://github.com/P-Adamiec/Free-Games-Claimer-Remaster), maintained by Paweł Adamiec and its contributors. That project was inspired by [vogler/free-games-claimer](https://github.com/vogler/free-games-claimer). Third-party notices are listed in [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md).

Distributed under the [GNU Affero General Public License v3.0](./LICENSE).
