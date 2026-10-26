#!/usr/bin/env python3
"""
Telegram Webhook Manager & Auto-Failover Watchdog for Speaking Coach AI Bot.

Features:
- Primary Domain:  https://speaking-coach-bot.tinonurcahya.dev/api/index
- Fallback Domain: https://speaking-coach-bot.vercel.app/api/index
- Auto-Failover: Automatically switches to fallback if primary domain is down/expired,
  and reverts back to primary once it is healthy.
"""

import argparse
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("webhook_manager")

PRIMARY_DOMAIN = "https://speaking-coach-bot.tinonurcahya.dev"
FALLBACK_DOMAIN = "https://speaking-coach-bot.vercel.app"
WEBHOOK_ENDPOINT = "/api/index"
HEALTH_ENDPOINT = "/health"


def get_credentials() -> tuple[str, str]:
    """Retrieve BOT_TOKEN and WEBHOOK_SECRET from environment or local .env."""
    bot_token = os.getenv("BOT_TOKEN")
    webhook_secret = os.getenv("WEBHOOK_SECRET")

    if not bot_token:
        # Try reading from local .env if present
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("WEBHOOK_SECRET="):
                        webhook_secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables or .env file.")
        sys.exit(1)

    return bot_token, webhook_secret or "tinoCoachSecret2026"


def get_current_webhook(bot_token: str) -> Dict[str, Any]:
    """Fetch current webhook information from Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SpeakingCoachWatchdog/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("result", {})
    except Exception as e:
        logger.error("Failed to query Telegram getWebhookInfo: %s", e)
        return {}


def set_webhook(bot_token: str, webhook_url: str, secret_token: str) -> bool:
    """Register a webhook URL with Telegram Bot API."""
    api_url = (
        f"https://api.telegram.org/bot{bot_token}/setWebhook"
        f"?url={urllib.parse.quote(webhook_url, safe='/:?=&')}"
        f"&secret_token={urllib.parse.quote(secret_token)}"
    )
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "SpeakingCoachWatchdog/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                logger.info("Successfully updated Telegram Webhook to: %s", webhook_url)
                return True
            logger.error("Telegram API error setting webhook: %s", data)
            return False
    except urllib.error.HTTPError as e:
        logger.error("HTTP error setting webhook: %s", e.read().decode())
        return False
    except Exception as e:
        logger.error("Exception setting webhook: %s", e)
        return False


def check_domain_health(base_url: str) -> bool:
    """Verify if target domain is reachable and healthy (returns HTTP 200)."""
    health_url = f"{base_url.rstrip('/')}{HEALTH_ENDPOINT}"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "SpeakingCoachWatchdog/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                body = resp.read().decode()
                try:
                    payload = json.loads(body)
                    return payload.get("status") == "ok"
                except Exception:
                    return True
            return False
    except Exception as e:
        logger.warning("Health check failed for %s: %s", health_url, e)
        return False


def run_auto_failover(bot_token: str, secret_token: str) -> None:
    """
    Intelligent Watchdog:
    - If PRIMARY is healthy, ensure webhook points to PRIMARY.
    - If PRIMARY is dead/expired and current is not FALLBACK, switch to FALLBACK.
    """
    current_info = get_current_webhook(bot_token)
    current_url = current_info.get("url", "")
    logger.info("Current active Telegram Webhook: %s", current_url or "(None)")

    target_primary = f"{PRIMARY_DOMAIN}{WEBHOOK_ENDPOINT}"
    target_fallback = f"{FALLBACK_DOMAIN}{WEBHOOK_ENDPOINT}"

    logger.info("Probing Primary Domain: %s ...", PRIMARY_DOMAIN)
    primary_healthy = check_domain_health(PRIMARY_DOMAIN)

    if primary_healthy:
        logger.info("Primary Domain (%s) is HEALTHY (OK).", PRIMARY_DOMAIN)
        if current_url != target_primary:
            logger.info("Promoting webhook to Primary Domain: %s", target_primary)
            set_webhook(bot_token, target_primary, secret_token)
        else:
            logger.info("Webhook is already correctly set to Primary Domain.")
    else:
        logger.warning("Primary Domain (%s) is UNREACHABLE / EXPIRED!", PRIMARY_DOMAIN)
        logger.info("Checking Fallback Domain: %s ...", FALLBACK_DOMAIN)
        fallback_healthy = check_domain_health(FALLBACK_DOMAIN)

        if fallback_healthy:
            if current_url != target_fallback:
                logger.warning("Activating emergency failover to Fallback Domain: %s", target_fallback)
                set_webhook(bot_token, target_fallback, secret_token)
            else:
                logger.info("Webhook is already operating on Fallback Domain.")
        else:
            logger.critical("Both Primary and Fallback domains failed health check!")


def main():
    parser = argparse.ArgumentParser(description="Speaking Coach Bot Webhook Manager & Failover Watchdog")
    parser.add_argument("--status", action="store_true", help="Print current active webhook info")
    parser.add_argument("--primary", action="store_true", help="Force set webhook to Primary (tinonurcahya.dev)")
    parser.add_argument("--fallback", action="store_true", help="Force set webhook to Fallback (vercel.app)")
    parser.add_argument("--auto", action="store_true", help="Run automated health check and failover watchdog")
    args = parser.parse_args()

    bot_token, secret_token = get_credentials()

    if args.status:
        info = get_current_webhook(bot_token)
        print(json.dumps(info, indent=2))
    elif args.primary:
        target = f"{PRIMARY_DOMAIN}{WEBHOOK_ENDPOINT}"
        set_webhook(bot_token, target, secret_token)
    elif args.fallback:
        target = f"{FALLBACK_DOMAIN}{WEBHOOK_ENDPOINT}"
        set_webhook(bot_token, target, secret_token)
    elif args.auto or len(sys.argv) == 1:
        run_auto_failover(bot_token, secret_token)


if __name__ == "__main__":
    main()
