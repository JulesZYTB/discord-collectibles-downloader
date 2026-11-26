# 📜 Changelog — Discord Collectibles Scraper

All notable changes, versions, and commits for **Discord Collectibles Scraper** are documented in this file.

---

## [v2.0.0] — 2026-11-26

### 🚀 Performance, Anti-Rate-Limit, Token Revocation Detection & Catalog Expansion

#### Commits & Impact

- **`ad02d7c` .. `8f0b9ad`** *(9 commits — 3,789 files added, ~2.75 GB)*
  - `8f0b9ad` — `feat: add new Discord avatar decorations and nameplates assets (part 1/9)` *(474 files)*
  - `c5e5131` — `feat: add new Discord avatar decorations and nameplates assets (part 2/9)` *(500 files)*
  - `47652e3` — `feat: add new Discord avatar decorations and nameplates assets (part 3/9)` *(500 files)*
  - `d89ce6f` — `feat: add new Discord avatar decorations and nameplates assets (part 4/9)` *(500 files)*
  - `008fdd6` — `feat: add new Discord avatar decorations and nameplates assets (part 5/9)` *(500 files)*
  - `44ec489` — `feat: add new Discord avatar decorations and nameplates assets (part 6/9)` *(436 files)*
  - `dbc6d85` — `feat: add new Discord avatar decorations and nameplates assets (part 7/9)` *(365 files)*
  - `c820ce5` — `feat: add new Discord avatar decorations and nameplates assets (part 8/9)` *(414 files)*
  - `ad02d7c` — `feat: add new Discord avatar decorations and nameplates assets (part 9/9)` *(100 files)*
  - **Impact:** Added 3,789 new Discord collectibles across `Avatar_Decorations/`, `Nameplates/`, `Profile_Borders/`, and `Profile_Effects/` (bringing the repository dataset to 6,834 files / ~4.82 GB). Split into 9 commits under 450 MB each to stay below GitHub's 2 GiB pack push limit.

- **`bfa7936`** — `perf(scraper): use batch storefront endpoints, anti-rate-limit headers, and token revocation detection` *(5 files changed: `main.py`, `src/config.py`, `src/downloader.py`, `src/scanner.py`, `src/utils.py` | +475 / -134 lines)*
  - **Impact — Batch Storefront API (~30x fewer API requests):**
    - Added bulk catalog & collection scanning via `/api/v9/collectibles-categories/v2` and paginated `/api/v9/storefront/collections/applications`.
    - Consolidated `/api/v9/shop/search` into a single combined `item_types` query (`limit=50`).
    - Replaced 1,700+ individual `/store/published-listings/skus/{sku_id}` calls with 30-SKU batch requests to `/api/v9/storefront/products/skus`.
  - **Impact — Anti-Rate-Limit & Anti-Revocation Headers:**
    - Added realistic Chrome 158 Discord Web headers (`X-Super-Properties`, `X-Discord-Locale`, `X-Discord-Timezone`, `Sec-CH-UA*`, `Referer: https://discord.com/shop`) in `src/utils.py`.
    - Separated `build_cdn_headers()` so `Authorization` is **never** sent to `cdn.discordapp.com`.
  - **Impact — Token Revocation Detection:**
    - Added upfront `GET /api/v9/users/@me` validation (`verify_token()`) and runtime `401` / `403` auth-failure detection.
    - Immediately prints `[✖ TOKEN REVOQUE / INVALIDE]` in the console and aborts cleanly instead of silently returning 0 items.
  - **Impact — Rate-Limit Pacing & CDN Resilience:**
    - Reads `X-RateLimit-Remaining` and `X-RateLimit-Reset-After` proactively, and handles HTTP `429` (`Retry-After` / `retry_after`) with jittered sleep & retry.
    - Increased CDN timeout to `12s`, capped proxy CDN workers to `16`, added direct-connection fallback on the final CDN retry, and fixed `parent_name` / `category` parsing so item names are not overwritten by accessibility descriptions.
    - Added `locale` configuration in `config.yaml` and wired `export_json` output in `main.py`.

---

## [v1.0.0] — 2026-07-20

### 🎉 Initial Release & First Collectibles Dataset

#### Commits & Impact

- **`64fa978`** — `feat: add collection of discord profile effects, avatar decorations, nameplates, and borders` *(3,045 files added)*
  - **Impact:** Published the initial archive of Discord collectibles (`Avatar_Decorations/`, `Nameplates/`, `Profile_Borders/`, `Profile_Effects/`).

- **`c91aa03`** — `docs: Update README.md with correct repo URLs, badges and clone instructions` *(2 files changed | +6 / -7 lines)*
  - **Impact:** Fixed GitHub repository links, star/fork badges, and `git clone` instructions in `README.md`.

- **`66c1d2a`** — `feat: Add full Discord Collectibles scraper source code, UI, multi-threaded downloader and proxy support` *(10 files added | +975 lines)*
  - **Impact:** Implemented the modular Python CLI architecture (`main.py`, `src/banner.py`, `src/config.py`, `src/downloader.py`, `src/menu.py`, `src/scanner.py`, `src/utils.py`, `.gitignore`, `README.md`) with interactive arrow-key navigation, YAML config persistence, proxy health checking, magic-bytes file extension detection, and multithreaded downloads.

- **`deed8c7`** — `first commit` *(1 file added | +157 lines)*
  - **Impact:** Initialized the repository with the MIT `LICENSE` and baseline project setup.
