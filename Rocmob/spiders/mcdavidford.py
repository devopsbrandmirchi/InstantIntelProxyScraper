import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy
from scrapy.http import Request

from Rocmob.rocmob_cfg import supabase

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _str(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(x) for x in value).strip()
    return str(value).strip()


def _playwright_proxy_config(session_id=None):
    """Build Playwright proxy dict from PROXY_URL / PROXY_AUTH (Scrapy meta proxy is ignored by PW)."""
    proxy_url = (os.getenv("PROXY_URL") or "").strip()
    if not proxy_url:
        return None

    parsed = urlparse(proxy_url if "://" in proxy_url else f"http://{proxy_url}")
    host = parsed.hostname
    if not host:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    server = f"{parsed.scheme or 'http'}://{host}:{port}"

    auth = (os.getenv("PROXY_AUTH") or "").strip()
    auth_list = [
        x.strip()
        for x in (os.getenv("PROXY_AUTH_LIST") or "").split(",")
        if x.strip()
    ]
    if auth_list:
        auth = auth_list[0] if not session_id else auth_list[hash(session_id) % len(auth_list)]

    cfg = {"server": server}
    if auth and ":" in auth:
        username, password = auth.split(":", 1)
        # Bright Data / Luminati: append -session-<id> to rotate egress IP per context
        if session_id and "-session-" not in username:
            username = f"{username}-session-{session_id}"
        cfg["username"] = username
        cfg["password"] = password
    return cfg


def _extract_bus2_state(html: str):
    """Parse SSR bootstrap for ws-inv-data / inventory-data-bus2 from page HTML."""
    match = re.search(
        r"DDC\.WS\.state\['ws-inv-data'\]\['inventory-data-bus2'\]\s*=\s*(\{)",
        html,
    )
    if not match:
        return None
    start = match.start(1)
    depth = 0
    in_str = False
    esc = False
    end = None
    for i, ch in enumerate(html[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if not end:
        return None
    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None


def _tracking_map(item: dict) -> dict:
    out = {}
    for entry in item.get("trackingAttributes") or []:
        if isinstance(entry, dict) and entry.get("name"):
            out[entry["name"]] = entry.get("value") or ""
    return out


def _attr_map(item: dict) -> dict:
    out = {}
    for entry in item.get("attributes") or []:
        if isinstance(entry, dict) and entry.get("name"):
            out[entry["name"]] = entry.get("value") or ""
    return out


def _pricing_fields(item: dict):
    """Return (msrp, price, savings) from pricing / trackingPricing."""
    tracking = item.get("trackingPricing") or {}
    pricing = item.get("pricing") or {}
    dprice = pricing.get("dprice") or []

    msrp = ""
    price = ""
    savings = ""

    for row in dprice:
        if not isinstance(row, dict):
            continue
        type_class = (row.get("typeClass") or "").lower()
        value = _str(row.get("value"))
        if type_class == "msrp" and value:
            msrp = value
        if row.get("isFinalPrice") and value:
            price = value
        if row.get("isDiscount") and value:
            savings = value

    if not msrp:
        msrp = _str(tracking.get("msrp") or pricing.get("retailPrice"))
    if not price:
        price = _str(
            tracking.get("internetPrice")
            or tracking.get("salePrice")
            or tracking.get("askingPrice")
        )
    if not savings:
        savings = _str(tracking.get("ABCRule") or "")

    return msrp, price, savings


class McdavidfordSpider(scrapy.Spider):
    name = "mcdavid"
    allowed_domains = ["mcdavidford.com"]

    # Legacy bus1 getInventory is deprecated (empty inventory + often 403).
    # Dealer.com now SSRs inventory into inventory-data-bus2 on listing pages.
    listing_url = "https://www.mcdavidford.com/all-inventory/index.htm"

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        # Droplet IP is rate-limited (429); Playwright ignores Scrapy ProxyMiddleware —
        # proxy is applied via playwright_context_kwargs from PROXY_URL/PROXY_AUTH.
        "ENABLE_PROXY": False,
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_TIMEOUT": 120,
        "RETRY_TIMES": 3,
        # Handle 429 ourselves with a fresh proxy session (Scrapy retries reuse same IP).
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408],
        "HTTPERROR_ALLOWED_CODES": [429],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
        self.total_count = None
        self.total_processed = 0
        self.inserted_count = 0
        self._session_id = uuid.uuid4().hex[:12]
        self._rate_limit_retries = {}

    def start_requests(self):
        proxy = _playwright_proxy_config(self._session_id)
        if proxy:
            self.logger.info(
                "Playwright proxy enabled: %s (session %s)",
                proxy.get("server"),
                self._session_id,
            )
        else:
            self.logger.warning(
                "No PROXY_URL set; Playwright will go direct and may hit 429 on the droplet."
            )
        yield self._listing_request(0)

    def _listing_request(self, start, session_id=None):
        session_id = session_id or self._session_id
        url = self.listing_url if start <= 0 else f"{self.listing_url}?start={start}"
        meta = {
            "page_start": start,
            "proxy_session": session_id,
            "playwright": True,
            # Unique context name so proxy session sticks for the crawl, and can rotate on 429.
            "playwright_context": f"mcdavid_{session_id}",
        }
        proxy = _playwright_proxy_config(session_id)
        context_kwargs = {
            "user_agent": USER_AGENT,
            "ignore_https_errors": True,
        }
        if proxy:
            context_kwargs["proxy"] = proxy
        meta["playwright_context_kwargs"] = context_kwargs
        return Request(
            url,
            callback=self.parse_listing,
            dont_filter=True,
            meta=meta,
        )

    def _retry_with_new_session(self, start: int, reason: str):
        key = str(start)
        attempts = self._rate_limit_retries.get(key, 0) + 1
        self._rate_limit_retries[key] = attempts
        if attempts > 6:
            self.logger.error(
                "Giving up on start=%s after %s rate-limit/empty-page retries (%s)",
                start,
                attempts,
                reason,
            )
            return None
        self._session_id = uuid.uuid4().hex[:12]
        self.logger.warning(
            "%s at start=%s; rotating Playwright proxy session to %s (attempt %s)",
            reason,
            start,
            self._session_id,
            attempts,
        )
        return self._listing_request(start, session_id=self._session_id)

    def parse_listing(self, response):
        page_start = int(response.meta.get("page_start") or 0)

        if response.status == 429:
            nxt = self._retry_with_new_session(page_start, "HTTP 429")
            if nxt:
                yield nxt
            return

        blob = _extract_bus2_state(response.text)
        if not blob:
            nxt = self._retry_with_new_session(
                page_start, "Missing inventory-data-bus2 SSR payload"
            )
            if nxt:
                yield nxt
            else:
                self.logger.error(
                    "Could not find inventory-data-bus2 SSR payload on %s", response.url
                )
            return

        wis = blob.get("WIS") or {}
        page_info = wis.get("pageInfo") or {}
        inventory = wis.get("inventory") or []
        accounts = blob.get("accounts") or {}

        total_count = int(page_info.get("totalCount") or 0)
        page_start = int(page_info.get("pageStart") or page_start)
        page_size = int(page_info.get("pageSize") or len(inventory) or 24)

        if self.total_count is None:
            self.total_count = total_count
            self.logger.info(
                "McDavid inventory via SSR bus2: totalCount=%s pageSize=%s",
                total_count,
                page_size,
            )

        if not inventory:
            nxt = self._retry_with_new_session(page_start, "Empty inventory page")
            if nxt:
                yield nxt
            return

        # Success for this page — clear retry counter
        self._rate_limit_retries.pop(str(page_start), None)

        for item in inventory:
            try:
                self._upsert_vehicle(item, accounts)
                self.total_processed += 1
            except Exception as exc:
                self.logger.error("Error processing vehicle: %s", exc)

        next_start = page_start + len(inventory)
        if (
            self.total_count
            and next_start < self.total_count
            and len(inventory) > 0
        ):
            yield self._listing_request(next_start)
        else:
            self.logger.info(
                "Finished: processed=%s totalCount=%s upserted=%s",
                self.total_processed,
                self.total_count,
                self.inserted_count,
            )

    def _upsert_vehicle(self, item: dict, accounts: dict):
        ta = _tracking_map(item)
        attrs = _attr_map(item)

        vin = _str(item.get("vin"))
        year = _str(item.get("year"))
        make = _str(item.get("make"))
        model = _str(item.get("model"))
        trim = _str(item.get("trim"))
        stock_number = _str(item.get("stockNumber") or attrs.get("stockNumber"))
        body_style = _str(item.get("bodyStyle"))
        condition_ = _str(item.get("condition") or item.get("type"))
        fuel_type = _str(item.get("fuelType") or ta.get("fuelType") or ta.get("normalFuelType"))
        transmission = _str(ta.get("transmission") or attrs.get("transmission"))
        engine = _str(ta.get("engine") or attrs.get("engine"))
        engine_size = _str(ta.get("engineSize"))
        if engine_size and engine_size not in engine:
            engine = f"{engine_size} {engine}".strip()
        drivetrain = _str(ta.get("driveLine"))
        doors = _str(ta.get("doors"))
        ext_color = _str(ta.get("exteriorColor") or attrs.get("exteriorColor"))
        int_color = _str(ta.get("interiorColor") or attrs.get("interiorColor"))
        odometer = _str(ta.get("odometer"))
        mileage_value = odometer or _str(attrs.get("fuelEconomy") or ta.get("cityFuelEconomy"))
        mileage_unit = "miles" if odometer else ("MPG" if mileage_value else "")

        msrp, price, savings = _pricing_fields(item)

        raw_link = _str(item.get("link"))
        url = f"https://www.mcdavidford.com{raw_link}" if raw_link.startswith("/") else raw_link
        title = _str(item.get("title")) or f"{condition_} {year} {make} {model}".strip()

        images = item.get("images") or []
        image_1 = images[0].get("uri", "") if len(images) > 0 and isinstance(images[0], dict) else ""
        image_2 = images[1].get("uri", "") if len(images) > 1 and isinstance(images[1], dict) else ""
        image_3 = images[2].get("uri", "") if len(images) > 2 and isinstance(images[2], dict) else ""

        account_id = _str(item.get("accountId"))
        account = accounts.get(account_id) or {}
        address = account.get("address") or {}
        location = _str(address.get("accountName") or account.get("name"))

        words = body_style.split(" ", 1)
        type_ = words[0] if words and words[0] else ""
        sub_type = words[1] if len(words) > 1 else ""

        if not vin:
            vin = f"TEMP-{stock_number or hashlib.md5((title + url).encode()).hexdigest()[:10]}"
            self.logger.warning("Missing VIN; using %s", vin)

        sk = hashlib.md5((vin + title + url).encode("utf-8")).hexdigest()

        row = {
            "sk": sk,
            "dealership_name": "David McDavid Ford",
            "dealer_type": "Auto",
            "dealership_address": "300 West Loop 820 S Fort Worth, TX 76108",
            "dealership_phone": _str(account.get("phone")),
            "store_code": "",
            "dealer_url": "https://www.mcdavidford.com/",
            "cms": "Dealer.com",
            "condition_": condition_,
            "year_": year,
            "make": make,
            "model": model,
            "brand": model,
            "vin": vin,
            "stock_number": stock_number,
            "url": url,
            "msrp": msrp,
            "price": price,
            "savings": savings,
            "finance_option": "",
            "special_tag": "",
            "type_": type_,
            "sub_type": sub_type,
            "location": location,
            "image_url": _str(image_1),
            "image_url_2": _str(image_2),
            "image_url_3": _str(image_3),
            "title": title,
            "description": "",
            "trim": trim,
            "length": "",
            "doors": doors,
            "drivetrain": drivetrain,
            "fuel_type": fuel_type,
            "exterior_color": ext_color,
            "interior_color": int_color,
            "sleeps": "",
            "seats": "",
            "dry_weight": "",
            "mileage_value": mileage_value,
            "mileage_unit": mileage_unit,
            "engine": engine,
            "transmission": transmission,
            "body_style": type_ or body_style,
            "features": "",
            "custom_label_0": "",
            "custom_label_1": "",
            "custom_label_2": "",
            "creation_date": self.creation_date,
        }

        try:
            supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
            self.inserted_count += 1
            self.logger.info("Upserted: %s", title)
        except Exception as exc:
            self.logger.error("Supabase error for %s: %s", url, exc)
