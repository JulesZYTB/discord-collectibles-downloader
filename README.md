# 🌌 DISCORD COLLECTIBLES SCRAPER by MrX 🚀

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/JulesZYTB/discord-collectibles-downloader?style=social)](https://github.com/JulesZYTB/discord-collectibles-downloader)
[![GitHub Forks](https://img.shields.io/github/forks/JulesZYTB/discord-collectibles-downloader?style=social)](https://github.com/JulesZYTB/discord-collectibles-downloader)

An ultra-modern, high-performance, modular CLI scraper for Discord profile collectibles: **Avatar Decorations**, **Profile Effects**, **Nameplates**, and **Profile Borders/Widgets**.

```text
  ██████╗ ██╗███████╗ ██████╗ ██████╗ ██████╗ ██████╗ 
  ██╔══██╗██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗
  ██║  ██║██║███████╗██║     ██║   ██║██████╔╝██║  ██║
  ██║  ██║██║╚════██║██║     ██║   ██║██╔══██╗██║  ██║
  ██████╔╝██║███████║╚██████╗╚██████╔╝██║  ██║██████╔╝
  ╚═════╝ ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ 
         DISCORD COLLECTIBLES SCRAPER by MrX
```

---

> ⚠️ **DISCLAIMER & LEGAL WARNING / AVERTISSEMENT LÉGAL**  
> 
> **[FR] À DES FINS ÉDUCATIVES UNIQUEMENT :**  
> Ce logiciel a été conçu exclusivement à des fins d'éducation, de recherche et d'apprentissage sur le fonctionnement des API web et le multithreading en Python. Les créateurs, développeurs et contributeurs de ce projet **déclinent toute responsabilité** quant à l'utilisation qui pourrait être faite de ce programme par des tiers. L'utilisateur est seul responsable du respect des Conditions Générales d'Utilisation (Terms of Service) des services tiers concernés.
> 
> **[EN] FOR EDUCATIONAL PURPOSES ONLY:**  
> This software is created strictly for educational, research, and learning purposes regarding Python multithreading and web API structures. The authors, developers, and maintainers **assume no responsibility or liability** for any misuse, damage, or violations caused by third parties using this software. Users are solely responsible for ensuring compliance with all applicable Terms of Service and local laws.

> 🔮 **UNRELEASED ASSETS & LEAKS / ÉLÉMENTS NON SORTIS**  
> 
> **[FR] DÉCOUVERTE D'ÉLÉMENTS INÉDITS :**  
> En raison de la puissance de notre scanner et de l'exploration directe des API Discord, il est possible que cet outil découvre et télécharge des décorations, effets ou éléments de boutique **pas encore publiés ni disponibles au grand public** (assets non sortis / unreleased). Désolé Discord pour les leaks ! 🤫👀
> 
> **[EN] UNRELEASED CONTENT DISCOVERY:**  
> Due to the deep direct API scanning algorithm, this tool may uncover and download **unreleased collectibles and upcoming shop assets** before they are officially released to the public. Sorry Discord for the leaks! 🤫👀

> 🌐 **PROXY RECOMMENDATION / RECOMMANDATION PROXY**  
> 
> **[FR] UTILISATION DE PROXY FORTEMENT RECOMMANDÉE :**  
> Pour scraper l'intégralité du catalogue Discord (plus de 3 000 assets) sans subir de ralentissements ou de blocages temporaires **HTTP 429 (Rate-Limited)**, il est **fortement recommandé de configurer un proxy** (ou une liste de proxys rotatifs) via le menu de configuration avancée (`⚙️ Configure Advanced Settings`) ou dans le fichier `config.yaml`.
> 
> **[EN] PROXY USAGE STRONGLY RECOMMENDED:**  
> When scraping large volumes of Discord Shop assets (3,000+ assets), using a proxy or rotating proxy list (configured via `⚙️ Configure Advanced Settings` or `config.yaml`) is **strongly recommended** to avoid Discord HTTP 429 rate limit delays.

---

## 🏗️ Project Architecture / Architecture Modulaire

```text
discord-collectibles-downloader/
├── main.py                     # Entry point (100% Interactive CLI + JSON export)
├── README.md                   # Full documentation & guide
├── changelogs.md               # Version history & per-commit impact log
├── LICENSE                     # MIT License
├── config.yaml                 # Auto-saved configuration settings (token, proxy, locale, threads)
├── .gitignore                  # Git ignore rules (protects config.yaml & *.har)
└── src/                        # Core modular engine
    ├── __init__.py
    ├── banner.py               # ASCII logo & ANSI neon themes
    ├── menu.py                 # Interactive Menu, Wizard & Token Prompt
    ├── config.py               # YAML configuration loader & saver
    ├── scanner.py              # Batch Storefront API Scanner, Token & Rate-Limit Guard
    ├── downloader.py           # Multithreaded CDN Downloader & Magic Bytes detector
    └── utils.py                # Chrome 158 / X-Super-Properties Headers, Proxy & Sanitizers
```

---

## ✨ Features / Fonctionnalités

- ⚡ **Batch Storefront API Scanner (v2.0)**: Queries `/collectibles-categories/v2`, `/storefront/collections/applications`, combined `/shop/search`, and 30-SKU batch `/storefront/products/skus` endpoints (~30x fewer API requests).
- 🔑 **Token Revocation Detection (v2.0)**: Verifies token validity upfront (`/users/@me`) and detects runtime `401`/`403` revocations with an explicit `[✖ TOKEN REVOQUE / INVALIDE]` console alert instead of failing silently.
- 🛡️ **Anti-Rate-Limit & Realistic Client Headers (v2.0)**: Sends modern Chrome 158 `X-Super-Properties` & locale headers to Discord APIs, never leaks `Authorization` to `cdn.discordapp.com`, proactively paces via `X-RateLimit-Remaining`, and retries `429` with `Retry-After`.
- 🔮 **Unreleased Collectibles Discovery**: Directly queries internal Discord API endpoints to uncover upcoming and unreleased collectibles.
- ⏱️ **Live Elapsed Timer & Speed Stats**: Real-time elapsed time counter (`⏱️ 00:45`) and speed tracker (`28.6 items/sec`) during scanning and downloading.
- 🧪 **Automatic Proxy Health Check & CDN Fallback**: Tests proxy status (`🟢 ON` / `🔴 OFF`) before scanning, caps proxy CDN concurrency, and falls back to direct connection on final CDN retry if a proxy drops.
- 🌐 **Universal Proxy Format Support**: Supports all proxy formats (`host:port:user:pass`, `user:pass@host:port`, `http://...`, `socks5://...`).
- 🎮 **100% Interactive Console Setup**: Navigate with keyboard **Arrow Keys (Up/Down)** and **Enter**, configure threads, proxies, locale, and JSON export (`catalog.json`).
- 🎨 **Modern Neon UI**: Vibrant ANSI color themes, ASCII headers, and live progress bars `[████████░░] 80%`.
- 🗂️ **Smart Categorization**: Automatically categorizes assets by item type (`Avatar_Decorations`, `Profile_Effects`, `Nameplates`, `Profile_Borders`) and official collection name.
- 🔍 **Magic Bytes Detector**: Verifies actual file header signatures (`.png`, `.webp`, `.gif`, `.mp4`, `.webm`).

---

## 📁 Output Folder Structure / Structure des Dossiers

```text
discord_collectibles/
├── Avatar_Decorations/      # Avatar decorations (PNG / WebP / APNG)
│   └── [Category_Name]/
│       ├── Static/
│       └── Animated/
├── Profile_Effects/         # Profile effects & animation layers (PNG / WebM)
│   └── [Category_Name]/
│       ├── Static/
│       └── Animated/
├── Nameplates/              # Profile nameplates (Static PNG & Animated Video)
│   └── [Category_Name]/
│       ├── Static/
│       └── Video/
└── Profile_Borders/         # Profile borders & custom widgets
    └── [Category_Name]/
        ├── Static/
        └── Video/
```

---

## 🚀 Quick Start / Guide Rapide

### Prerequisites
- **Python 3.9+** (No external third-party dependencies required! Uses Python standard library).

### Installation
```bash
git clone https://github.com/JulesZYTB/discord-collectibles-downloader.git
cd discord-collectibles-downloader
```

### Basic Usage
Launch the interactive app:

```bash
python main.py
```

### Interactive Menu Options:
```text
  Main Menu - Select an Action:

  ❯ 🚀 Start Full Scraper (Download Everything)
    🎭 Download Avatar Decorations Only
    ✨ Download Profile Effects Only
    📛 Download Nameplates Only
    🖼️  Download Profile Borders Only
    ⚙️  Configure Advanced Settings (Threads, Proxy, Output path)
    ❌ Exit
```

---

## 🏷️ GitHub Search Topics & Tags / Mots-clés

`discord` • `discord-scraper` • `discord-api` • `discord-profile-effects` • `discord-avatar-decorations` • `discord-nameplates` • `discord-collectibles` • `discord-shop` • `discord-assets` • `python-scraper` • `asset-downloader` • `profile-effects` • `avatar-decorations` • `nameplates` • `discord-media-downloader` • `discord-tools` • `discord-shop-api` • `open-source` • `cli-menu`

---

## 📜 Changelog & License

- Full version history and per-commit impact are documented in [changelogs.md](changelogs.md).
- Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

⭐ **If you find this project useful, don't forget to give it a star on GitHub!** ⭐
