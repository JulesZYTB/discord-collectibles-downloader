import sys
import json
import time
import ssl
import random
import threading
import itertools
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

from .banner import C_PURPLE, C_CYAN, C_BLUE, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_DIM, C_RESET
from .utils import (
    sanitize_name,
    parse_proxy,
    test_proxy_connection,
    build_discord_api_headers,
    build_cdn_headers,
)

# Create unverified SSL context for proxy compatibility (fixes SSL handshake errors)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

DISCORD_APP_ID = "1096190356233670716"
SKU_BATCH_SIZE = 30


def format_elapsed_time(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class DiscordCatalogScanner:
    def __init__(self, token="", proxies=None, retries=3, locale="en-US"):
        self.token = token.strip() if token else ""
        self.retries = max(1, int(retries))
        self.locale = locale or "en-US"
        self.seen_urls = set()
        self.resolved_skus = set()
        self.items = []
        self.target_filter = None
        self.scan_start_time = None

        self.token_revoked = False
        self.token_error_reason = ""
        self._lock = threading.Lock()
        self._rate_limit_hits = 0

        parsed_proxies = []
        if proxies:
            for p in proxies:
                norm_p = parse_proxy(p)
                if norm_p:
                    parsed_proxies.append(norm_p)

        self.proxies = parsed_proxies
        self.proxy_pool = itertools.cycle(self.proxies) if self.proxies else None

    def get_next_proxy(self):
        if self.proxy_pool:
            with self._lock:
                return next(self.proxy_pool)
        return None

    def _mark_token_revoked(self, status_code, body_text=""):
        """Thread-safe flag & immediate console alert when token is invalid or revoked."""
        detail = ""
        if body_text:
            try:
                err_json = json.loads(body_text)
                msg = err_json.get("message", "")
                code = err_json.get("code", "")
                if msg or code:
                    detail = f" ({msg} - code {code})" if code else f" ({msg})"
            except Exception:
                pass

        with self._lock:
            if not self.token_revoked:
                self.token_revoked = True
                self.token_error_reason = f"HTTP {status_code}{detail}"
                sys.stdout.write(
                    f"\n\n{C_RED}{C_BOLD}[✖ TOKEN REVOQUE / INVALIDE]{C_RESET} "
                    f"{C_RED}Discord a rejete le token ({self.token_error_reason}).{C_RESET}\n"
                    f"{C_YELLOW}[!] Le token est expire, revoque ou le compte est restreint. "
                    f"Mets a jour ton token dans config.yaml.{C_RESET}\n\n"
                )
                sys.stdout.flush()

    def _is_auth_failure(self, status_code, body_text):
        """Distinguish token revocation/invalidity from ordinary 403/404."""
        if status_code == 401:
            return True
        if status_code == 403:
            lowered = body_text.lower()
            if any(k in lowered for k in ("unauthorized", "token", "verify your account", "suspended", "disabled", "40001", "40002", "40003")):
                return True
        return False

    def download_url(self, url, timeout=10, max_retries=None):
        """Fetch API JSON or CDN asset with rate-limit backoff and token revocation detection."""
        is_api = "discord.com/api/" in url
        if is_api and self.token_revoked:
            return None, ""

        attempts = max_retries if max_retries is not None else self.retries

        for attempt in range(1, attempts + 1):
            if is_api and self.token_revoked:
                return None, ""

            # For CDN assets, fall back to direct connection on final retry if proxy is flaky
            use_proxy = self.get_next_proxy()
            if not is_api and attempt == attempts and use_proxy:
                use_proxy = None

            headers = (
                build_discord_api_headers(self.token, locale=self.locale)
                if is_api
                else build_cdn_headers()
            )

            req = urllib.request.Request(url, headers=headers)
            https_handler = urllib.request.HTTPSHandler(context=SSL_CONTEXT)

            if use_proxy:
                proxy_handler = urllib.request.ProxyHandler({"http": use_proxy, "https": use_proxy})
                opener = urllib.request.build_opener(proxy_handler, https_handler)
            else:
                opener = urllib.request.build_opener(https_handler)

            try:
                with opener.open(req, timeout=timeout) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    data = resp.read()

                    # Proactive rate-limit pacing on Discord API buckets
                    if is_api:
                        remaining = resp.headers.get("X-RateLimit-Remaining")
                        reset_after = resp.headers.get("X-RateLimit-Reset-After")
                        if remaining == "0" and reset_after:
                            try:
                                wait_s = min(float(reset_after) + 0.15, 10.0)
                                if wait_s > 0:
                                    time.sleep(wait_s)
                            except ValueError:
                                pass

                    return data, content_type

            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass

                if is_api and self._is_auth_failure(e.code, err_body):
                    self._mark_token_revoked(e.code, err_body)
                    return None, ""

                if e.code == 429:
                    self._rate_limit_hits += 1
                    retry_after = 2.0
                    header_ra = e.headers.get("Retry-After") or e.headers.get("X-RateLimit-Reset-After")
                    if header_ra:
                        try:
                            retry_after = float(header_ra)
                        except ValueError:
                            pass
                    elif err_body:
                        try:
                            retry_after = float(json.loads(err_body).get("retry_after", 2.0))
                        except Exception:
                            pass

                    wait_s = min(max(retry_after, 0.5), 30.0) + random.uniform(0.25, 0.75)
                    if is_api:
                        sys.stdout.write(
                            f"\r\033[K  {C_YELLOW}[⏳ RATE LIMIT 429]{C_RESET} "
                            f"Pause {wait_s:.1f}s avant retry ({attempt}/{attempts})...\n"
                        )
                        sys.stdout.flush()
                    time.sleep(wait_s)
                    continue

                if e.code in (401, 403, 404):
                    return None, ""

                time.sleep(0.25 * attempt + random.uniform(0.05, 0.2))

            except Exception:
                time.sleep(0.25 * attempt + random.uniform(0.05, 0.2))

        return None, ""

    def verify_token(self):
        """Verify Discord token upfront using /api/v9/users/@me before scanning."""
        if not self.token:
            self._mark_token_revoked(401, '{"message": "Token manquant"}')
            return False

        print(f"  {C_BLUE}[🔑 AUTH CHECK]{C_RESET} Verification du token Discord...")
        data_bytes, _ = self.download_url("https://discord.com/api/v9/users/@me", timeout=8, max_retries=2)
        if self.token_revoked:
            return False
        if not data_bytes:
            print(f"  {C_YELLOW}[!] Impossible de joindre /users/@me (reseau/proxy), poursuite du scan...{C_RESET}")
            return True

        try:
            user_info = json.loads(data_bytes.decode("utf-8", errors="ignore"))
            username = user_info.get("username", "unknown")
            print(f"  {C_GREEN}[✔ TOKEN VALIDE]{C_RESET} Connecte en tant que {C_BOLD}{username}{C_RESET}\n")
        except Exception:
            pass
        return True

    def add_item(self, kind, category, name, url, subtype="Static", item_id=""):
        if not url:
            return

        sanitized_kind = sanitize_name(kind, 30)
        if self.target_filter and sanitized_kind.lower() != self.target_filter.lower():
            return

        with self._lock:
            if url in self.seen_urls:
                return
            self.seen_urls.add(url)
            item = {
                "kind": sanitized_kind,
                "category": sanitize_name(category, 50),
                "name": sanitize_name(name, 50),
                "url": url,
                "subtype": sanitize_name(subtype, 20),
                "item_id": sanitize_name(str(item_id), 40) if item_id else "",
            }
            self.items.append(item)
            total_now = len(self.items)

        elapsed_str = format_elapsed_time(time.time() - self.scan_start_time) if self.scan_start_time else "00:00"
        sys.stdout.write(
            f"\r\033[K  {C_GREEN}[✨ DISCOVERED]{C_RESET} {C_PURPLE}{sanitized_kind}{C_RESET} | "
            f"{C_CYAN}{item['category']}{C_RESET} : {C_BOLD}{item['name'][:25]}{C_RESET} "
            f"{C_DIM}(Total: {total_now}){C_RESET} | ⏱️ {C_YELLOW}{elapsed_str}{C_RESET}\n"
        )
        sys.stdout.flush()

    def parse_json_payload(self, data, current_cat="General", parent_name=""):
        if isinstance(data, dict):
            # Unpack published-listings wrapper if present
            if "sku" in data and isinstance(data["sku"], dict):
                self.parse_json_payload(data["sku"], current_cat, parent_name)
                return

            # Only collections/categories (objects holding "products") define a new category name
            cat_name = data.get("name", current_cat) if "products" in data else current_cat

            # Check tenant_metadata for true collectibles item data & type
            collectibles_meta = data.get("tenant_metadata", {}).get("collectibles", {})
            item_meta = collectibles_meta.get("item", {}) if isinstance(collectibles_meta, dict) else {}

            item_type = None
            if isinstance(collectibles_meta, dict) and "type" in collectibles_meta:
                item_type = collectibles_meta["type"]
            elif isinstance(item_meta, dict) and "type" in item_meta:
                item_type = item_meta["type"]
            else:
                item_type = data.get("type")

            sku_id = data.get("sku_id") or data.get("id")
            prod_name = data.get("name") or data.get("title") or parent_name

            if item_type is not None and sku_id:
                with self._lock:
                    self.resolved_skus.add(str(sku_id))

                # Prefer explicit name/title or parent product name over accessibility "label"
                label = data.get("name") or data.get("title") or parent_name or data.get("label") or sku_id

                # Type 0: Avatar Decoration
                if item_type == 0:
                    asset_hash = data.get("asset") or item_meta.get("asset")
                    if asset_hash:
                        is_anim = str(asset_hash).startswith("a_")
                        self.add_item(
                            "Avatar_Decorations",
                            cat_name,
                            label,
                            f"https://cdn.discordapp.com/avatar-decoration-presets/{asset_hash}.png?size=1024",
                            "Animated" if is_anim else "Static",
                            asset_hash,
                        )

                # Type 1: Profile Effect
                elif item_type == 1:
                    effects = data.get("effects", []) or item_meta.get("effects", [])
                    for idx, eff in enumerate(effects):
                        if isinstance(eff, dict) and eff.get("src"):
                            self.add_item("Profile_Effects", cat_name, f"{label}_layer_{idx}", eff.get("src"), "Animated", f"{sku_id}_{idx}")
                    for key in ["staticFrameSrc", "static_frame_src", "thumbnailPreviewSrc", "thumbnail_preview_src", "reducedMotionSrc", "reduced_motion_src"]:
                        src = data.get(key) or item_meta.get(key)
                        if src:
                            self.add_item("Profile_Effects", cat_name, f"{label}_{key}", src, "Static", sku_id)

                # Type 2: Nameplate
                elif item_type == 2:
                    asset_path = data.get("asset") or item_meta.get("asset")
                    asset_id = sku_id
                    if asset_path and isinstance(asset_path, str):
                        parts = [p for p in asset_path.split("/") if p]
                        if parts:
                            asset_id = parts[-1]

                    assets_dict = data.get("assets") or item_meta.get("assets")
                    if isinstance(assets_dict, dict):
                        for sub_key, sub_path in assets_dict.items():
                            if sub_path and isinstance(sub_path, str):
                                full_url = sub_path if sub_path.startswith("http") else f"https://cdn.discordapp.com/{sub_path}"
                                subtype = "Animated" if ("video" in sub_key or "anim" in sub_key) else "Static"
                                self.add_item("Nameplates", cat_name, f"{label}_{sub_key}", full_url, subtype, asset_id)

                    asset_url = data.get("asset_url") or item_meta.get("asset_url")
                    if asset_url:
                        self.add_item("Nameplates", cat_name, label, asset_url, "Static", asset_id)

                    self.add_item("Nameplates", cat_name, label, f"https://cdn.discordapp.com/media/v1/collectibles-shop/{sku_id}/static", "Static", sku_id)
                    self.add_item("Nameplates", cat_name, label, f"https://cdn.discordapp.com/media/v1/collectibles-shop/{sku_id}/video", "Video", sku_id)

                # Type 3: Profile Border / Widget / Frame
                elif item_type == 3:
                    layers = data.get("layers", []) or item_meta.get("layers", [])
                    for layer in layers:
                        layer_id = layer.get("id") if isinstance(layer, dict) else layer
                        if layer_id:
                            self.add_item(
                                "Profile_Borders",
                                cat_name,
                                f"{label}_layer_{layer_id}",
                                f"https://cdn.discordapp.com/media/v1/collectibles-shop/{sku_id}/{layer_id}/static",
                                "Static",
                                layer_id,
                            )

                    for key in ["asset_url", "src", "static_frame_src", "thumbnail_preview_src", "hero_banner_url", "popout_asset", "asset"]:
                        src = data.get(key) or item_meta.get(key)
                        if src and isinstance(src, str) and src.startswith("http"):
                            self.add_item("Profile_Borders", cat_name, label, src, "Static", sku_id)

            for k, v in data.items():
                if k in ("categories", "collections") and isinstance(v, list):
                    for cat in v:
                        if isinstance(cat, dict):
                            self.parse_json_payload(cat, cat.get("name", cat_name), "")
                elif k == "products" and isinstance(v, list):
                    for prod in v:
                        if isinstance(prod, dict):
                            self.parse_json_payload(prod, cat_name, prod.get("name", ""))
                elif isinstance(v, (dict, list)):
                    self.parse_json_payload(v, cat_name, prod_name)

        elif isinstance(data, list):
            for elem in data:
                if isinstance(elem, dict):
                    self.parse_json_payload(elem, current_cat, parent_name)

    def _scan_storefront_collections(self):
        """Fetch full collections from /storefront/collections/applications (reduces API calls dramatically)."""
        offset = 0
        limit = 10
        while not self.token_revoked:
            url = (
                f"https://discord.com/api/v9/storefront/collections/applications"
                f"?country_code=FR&application_id={DISCORD_APP_ID}&use_shop_ordering=true"
                f"&offset={offset}&limit={limit}&include_pricing=false&locale={urllib.parse.quote(self.locale)}"
                f"&with_bundled_skus=true&include_google_sku_ids=false"
                f"&include_unpublished_products=false&include_unpublished_collections=false&ignore_cache=false"
            )
            data_bytes, _ = self.download_url(url, timeout=10)
            if not data_bytes or self.token_revoked:
                break
            try:
                res = json.loads(data_bytes.decode("utf-8", errors="ignore"))
                cols = res.get("collections", [])
                total = res.get("total", 0)
                if not cols:
                    break
                self.parse_json_payload(res)
                offset += len(cols)
                if total and offset >= total:
                    break
                time.sleep(random.uniform(0.15, 0.35))
            except Exception:
                break

    def scan_catalog(self, filter_kind=None, mode_title="🚀 Full Scraper (Download Everything)"):
        self.target_filter = filter_kind
        self.scan_start_time = time.time()

        # Test Proxy Health if configured
        if self.proxies:
            active_proxy = self.proxies[0]
            print(f"\n{C_CYAN}[🧪 PROXY CHECK]{C_RESET} Testing proxy connection: {C_DIM}{active_proxy}{C_RESET}...")
            is_ok, reason = test_proxy_connection(active_proxy)
            if is_ok:
                print(f"  {C_GREEN}[✔ PROXY ONLINE] Connection successful! ({reason}){C_RESET}\n")
                proxy_status = f"{C_GREEN}{C_BOLD}🟢 ON{C_RESET} {C_DIM}({active_proxy[:40]}){C_RESET}"
            else:
                print(f"  {C_RED}[✖ PROXY ERROR] Proxy check failed: {reason}{C_RESET}\n")
                print(f"  {C_YELLOW}[!] Your configured proxy is unresponsive or rejected authentication.{C_RESET}")
                print(f"  {C_BOLD}➔ Continue with Direct Connection (without proxy)? (y/n) [y]: {C_RESET}", end="")
                try:
                    choice = input().strip().lower()
                    if choice in ("", "y", "yes"):
                        print(f"  {C_CYAN}[!] Switched to Direct Connection.{C_RESET}\n")
                        self.proxies = []
                        self.proxy_pool = None
                        proxy_status = f"{C_RED}{C_BOLD}🔴 OFF{C_RESET} {C_DIM}(Direct Connection - Proxy Failed){C_RESET}"
                    else:
                        print(f"  {C_RED}[!] Aborting scan due to proxy failure.{C_RESET}\n")
                        return []
                except Exception:
                    self.proxies = []
                    self.proxy_pool = None
                    proxy_status = f"{C_RED}{C_BOLD}🔴 OFF{C_RESET} {C_DIM}(Direct Connection){C_RESET}"
        else:
            proxy_status = f"{C_RED}{C_BOLD}🔴 OFF{C_RESET} {C_DIM}(Direct Connection){C_RESET}"

        print(f"\n{C_PURPLE}{C_BOLD}======================================================{C_RESET}")
        print(f"  {C_YELLOW}{C_BOLD}🎯 SELECTED MODE:{C_RESET} {C_CYAN}{C_BOLD}{mode_title}{C_RESET}")
        print(f"  {C_YELLOW}{C_BOLD}🌐 PROXY STATUS : {C_RESET} {proxy_status}")
        print(f"{C_PURPLE}{C_BOLD}======================================================{C_RESET}")
        print(f"\n{C_CYAN}{C_BOLD}[*] LIVE CATALOG SCANNER INITIALIZED...{C_RESET}\n")

        # Upfront token validation
        if not self.verify_token():
            return []

        # Phase 1: Bulk Shop Catalog, Categories v2 & Storefront Collections
        endpoints = [
            f"https://discord.com/api/v9/collectibles-categories/v2?include_bundles=true&variants_return_style=2&skip_num_categories=0&locale={urllib.parse.quote(self.locale)}",
            f"https://discord.com/api/v9/collectibles-shop?tab=home&include_bundles=true&include_dynamic_blocks=true&variants_return_style=2&skip_num_categories=0&locale={urllib.parse.quote(self.locale)}",
            "https://discord.com/api/v9/users/@me/collectibles-marketing?platform=0",
        ]

        for ep in endpoints:
            if self.token_revoked:
                break
            print(f"  {C_BLUE}[🔍 API SCAN]{C_RESET} Querying bulk catalog: {C_DIM}{ep[:68]}...{C_RESET}")
            data_bytes, _ = self.download_url(ep, timeout=12)
            if data_bytes:
                try:
                    self.parse_json_payload(json.loads(data_bytes.decode("utf-8", errors="ignore")))
                except Exception:
                    pass
            time.sleep(random.uniform(0.15, 0.35))

        if not self.token_revoked:
            print(f"  {C_BLUE}[📦 COLLECTIONS]{C_RESET} Fetching storefront collections...")
            self._scan_storefront_collections()

        # Phase 2: /shop/search for any remaining SKUs (single combined item_types query)
        kind_api_map = {
            "avatar_decorations": ["AVATAR_DECORATION"],
            "profile_effects": ["PROFILE_EFFECT"],
            "nameplates": ["NAMEPLATE"],
            "profile_borders": ["PROFILE_FRAME"],
        }

        if filter_kind and filter_kind.lower() in kind_api_map:
            item_types = kind_api_map[filter_kind.lower()]
        else:
            item_types = ["AVATAR_DECORATION", "NAMEPLATE", "PROFILE_EFFECT", "PROFILE_FRAME", "BUNDLE"]

        missing_skus = []
        seen_search_skus = set()

        if not self.token_revoked:
            print(f"\n  {C_BLUE}[🔍 SHOP SEARCH]{C_RESET} Checking search index ({', '.join(item_types)})...")
            type_params = "&".join(f"item_types={t}" for t in item_types)
            offset = 0
            limit = 50
            while not self.token_revoked:
                api_url = (
                    f"https://discord.com/api/v9/shop/search?{type_params}"
                    f"&offset={offset}&limit={limit}&sort_type=popularity&sort_direction=desc"
                    f"&published_collections_only=true"
                )
                data_bytes, _ = self.download_url(api_url, timeout=8)
                if not data_bytes or self.token_revoked:
                    break
                try:
                    res_json = json.loads(data_bytes.decode("utf-8", errors="ignore"))
                    skus = res_json.get("skus", [])
                    pagination = res_json.get("pagination", {})
                    total_available = pagination.get("total", 0)
                    has_more = pagination.get("has_more", False)

                    if not skus:
                        break

                    for sku_item in skus:
                        if isinstance(sku_item, dict):
                            self.parse_json_payload(sku_item, current_cat="Shop_Search")
                        elif isinstance(sku_item, str):
                            if sku_item not in self.resolved_skus and sku_item not in seen_search_skus:
                                seen_search_skus.add(sku_item)
                                missing_skus.append(sku_item)

                    offset += len(skus)
                    if not has_more or (total_available > 0 and offset >= total_available):
                        break
                    time.sleep(random.uniform(0.1, 0.25))
                except Exception:
                    break

        # Phase 3: Batch-resolve remaining SKUs via /storefront/products/skus (30 per request)
        if missing_skus and not self.token_revoked:
            batches = [missing_skus[i:i + SKU_BATCH_SIZE] for i in range(0, len(missing_skus), SKU_BATCH_SIZE)]
            print(
                f"\n  {C_BLUE}[⚡ BATCH RESOLVE]{C_RESET} Resolving {len(missing_skus)} remaining SKUs "
                f"in {len(batches)} batch requests (30/req)..."
            )

            def fetch_sku_batch(sku_batch):
                if self.token_revoked:
                    return None
                time.sleep(random.uniform(0.15, 0.4))
                sku_params = "&".join(f"sku_ids={s}" for s in sku_batch)
                batch_url = (
                    f"https://discord.com/api/v9/storefront/products/skus"
                    f"?country_code=FR&{sku_params}&locale={urllib.parse.quote(self.locale)}"
                    f"&with_bundled_skus=true&include_google_sku_ids=false&ignore_cache=false"
                )
                detail_bytes, _ = self.download_url(batch_url, timeout=10)
                if detail_bytes:
                    try:
                        return json.loads(detail_bytes.decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
                return None

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(fetch_sku_batch, b) for b in batches]
                for future in as_completed(futures):
                    if self.token_revoked:
                        break
                    batch_json = future.result()
                    if batch_json:
                        self.parse_json_payload(batch_json, current_cat="Shop_Batch")

        print("\n")
        total_scan_duration = time.time() - self.scan_start_time

        if self.token_revoked:
            print(f"{C_RED}{C_BOLD}================ SCAN INTERROMPU (TOKEN REVOQUE) ================{C_RESET}")
            print(f"  {C_RED}✖ Raison : {self.token_error_reason}{C_RESET}")
            print(f"  {C_YELLOW}➜ Mets a jour ton token Discord dans config.yaml avant de relancer.{C_RESET}")
            print(f"{C_RED}{C_BOLD}==================================================================={C_RESET}\n")

        # Print catalog breakdown summary
        kind_counts = {}
        for item in self.items:
            k = item["kind"]
            kind_counts[k] = kind_counts.get(k, 0) + 1

        print(f"\n{C_PURPLE}{C_BOLD}================ CATALOG BREAKDOWN ================{C_RESET}")
        for k, count in kind_counts.items():
            print(f"  • {C_CYAN}{k:<20}{C_RESET} : {C_GREEN}{C_BOLD}{count}{C_RESET} assets discovered")
        print(f"  ------------------------------------------------")
        print(f"  {C_BOLD}Total Assets To Download : {C_YELLOW}{len(self.items)}{C_RESET}")
        print(f"  ⏱️  Total Catalog Scan Time: {C_BOLD}{format_elapsed_time(total_scan_duration)}{C_RESET}")
        if self._rate_limit_hits:
            print(f"  {C_YELLOW}⏳ Rate-limits geres      : {self._rate_limit_hits}{C_RESET}")
        print(f"{C_PURPLE}{C_BOLD}==================================================={C_RESET}\n")

        return self.items
