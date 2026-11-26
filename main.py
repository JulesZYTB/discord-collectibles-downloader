#!/usr/bin/env python3
"""
     🌌 DISCORD COLLECTIBLES SCRAPER by MrX 🚀
     ===========================================
 Main Entry Point (Fully Interactive Console App with YAML config)
"""

import json
import sys

from src.banner import enable_ansi_windows, C_CYAN, C_GREEN, C_RED, C_RESET
from src.config import load_config
from src.menu import interactive_select, prompt_mandatory_token, prompt_advanced_settings
from src.scanner import DiscordCatalogScanner
from src.downloader import AssetDownloader
from src.utils import parse_proxy


def main():
    enable_ansi_windows()

    # Load configuration from config.yaml if present
    settings = load_config()

    while True:
        options = [
            "🚀 Start Full Scraper (Download Everything)",
            "🎭 Download Avatar Decorations Only",
            "✨ Download Profile Effects Only",
            "📛 Download Nameplates Only",
            "🖼️  Download Profile Borders Only",
            "⚙️  Configure Advanced Settings (Threads, Proxy, Output path)",
            "❌ Exit"
        ]

        selected_choice = interactive_select("Main Menu - Select an Action:", options)

        if selected_choice == 5:
            # Advanced Settings Wizard
            settings = prompt_advanced_settings(settings)
            continue
        elif selected_choice == 6:
            # Exit
            print(f"\n{C_CYAN}Goodbye! {C_RESET}")
            sys.exit(0)

        # Action selected - Prompt Mandatory Token if missing
        token = prompt_mandatory_token(settings)

        kind_map = {
            0: None,
            1: "Avatar_Decorations",
            2: "Profile_Effects",
            3: "Nameplates",
            4: "Profile_Borders"
        }
        filter_kind = kind_map.get(selected_choice)
        mode_title = options[selected_choice]

        raw_proxy = settings.get("proxy", "")
        norm_proxy = parse_proxy(raw_proxy)
        proxies = [norm_proxy] if norm_proxy else []

        # Run Scanner & Downloader
        scanner = DiscordCatalogScanner(
            token=token,
            proxies=proxies,
            retries=settings.get("retries", 3),
            locale=settings.get("locale", "en-US"),
        )
        items = scanner.scan_catalog(filter_kind=filter_kind, mode_title=mode_title)

        if settings.get("export_json") and items:
            try:
                with open(settings["export_json"], "w", encoding="utf-8") as jf:
                    json.dump(items, jf, indent=2, ensure_ascii=False)
                print(f"{C_GREEN}[✔] Exported catalog metadata to {settings['export_json']}{C_RESET}")
            except Exception as e:
                print(f"{C_RED}[!] Failed to export JSON: {e}{C_RESET}")

        downloader = AssetDownloader(
            output_dir=settings.get("output", "discord_collectibles"),
            scanner=scanner,
            max_workers=settings.get("threads", 16),
        )
        downloader.download_all(items)

        if scanner.token_revoked:
            print(f"{C_RED}[✖] Tache arretee : token Discord revoque ou invalide.{C_RESET}\n")
        else:
            print(f"{C_GREEN}[✔] Scraping task completed!{C_RESET}\n")
        break


if __name__ == "__main__":
    main()
