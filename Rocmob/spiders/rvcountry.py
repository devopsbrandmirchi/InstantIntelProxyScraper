import hashlib
from datetime import datetime, timezone
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request

from Rocmob.rocmob_cfg import supabase


class RvcountrySpider(scrapy.Spider):
    name = "rvcountry"
    allowed_domains = ["inventory.coasttechnology.org", "rvcountry.com"]

    inventory_page = "https://rvcountry.com/rvs-for-sale"
    api_url = "https://inventory.coasttechnology.org/api/v3/inventory/"
    company_id = "36"
    location_name = "Fresno CA"
    per_page = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def start_requests(self):
        yield self._inventory_request(page=1)

    def _inventory_request(self, page):
        params = {
            "filters[displayOnWebsite][$eq]": "true",
            "filters[lot][$ne]": "BGN",
            "filters[companyLocation][name][$in][0]": self.location_name,
            "sort[0]": "year:desc",
            "sort[1]": "received_date:desc",
            "company[0]": self.company_id,
            "withUnitData": "1",
            "page": str(page),
            "per_page": str(self.per_page),
        }
        return Request(
            url=f"{self.api_url}?{urlencode(params)}",
            callback=self.parse_inventory,
            errback=self.handle_error,
            meta={"page": page},
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.inventory_page,
                "Origin": "https://rvcountry.com",
            },
        )

    def parse_inventory(self, response):
        try:
            payload = response.json()
        except ValueError as exc:
            self.logger.error("Invalid JSON on page %s: %s", response.meta.get("page"), exc)
            return

        for item in payload.get("data") or []:
            self._upsert_item(item)

        pagination = payload.get("pagination") or {}
        current_page = pagination.get("current_page") or response.meta.get("page", 1)
        last_page = pagination.get("last_page")
        if last_page and current_page < last_page:
            yield self._inventory_request(page=current_page + 1)

    def handle_error(self, failure):
        self.logger.error("Inventory request failed: %s", failure.value)

    def _upsert_item(self, item):
        url = self._rvcountry_url(item.get("urls") or [])
        if not url:
            self.logger.debug("Skipping unit %s without rvcountry.com URL", item.get("id"))
            return

        title = (item.get("title") or "").strip()
        vin = (item.get("vin") or "").strip()
        stock_number = (item.get("stock_number") or "").strip()

        location_info = item.get("company_location") or {}
        city = (location_info.get("city") or "").strip()
        state = (location_info.get("state") or "").strip()
        location = ", ".join(part for part in (city, state) if part)
        dealership_name = "RV Country Fresno"

        address_parts = [
            (location_info.get("address") or "").strip(),
            city,
            state,
            (location_info.get("zip") or "").strip(),
        ]
        dealership_address = ", ".join(part for part in address_parts if part)
        dealership_phone = (location_info.get("phone") or "").strip()
        store_code = (item.get("lot") or "").strip()

        unit_classification = item.get("unit_classification") or {}
        vehicle_type = unit_classification.get("vehicle_type") or {}

        condition = (item.get("condition") or {}).get("name") or ""
        year = item.get("year")
        if year in (None, 0, ""):
            year = (item.get("inventory_units") or {}).get("year")
        year = str(year) if year not in (None, 0, "") else ""

        make = ((item.get("unit_make") or {}).get("name") or "").strip()
        model = ((item.get("unit_model") or {}).get("name") or "").strip()
        trim = ((item.get("unit_trim") or {}).get("name") or "").strip()
        brand = model

        type_ = (unit_classification.get("name") or "").strip()
        sub_type = (vehicle_type.get("name") or "").strip()

        msrp = self._format_price(item.get("price_msrp"))
        price = self._format_price(item.get("price_current"))
        savings = self._format_price(item.get("price_current_savings"))
        if not savings and item.get("price_msrp") and item.get("price_current"):
            try:
                savings = self._format_price(float(item["price_msrp"]) - float(item["price_current"]))
            except (TypeError, ValueError):
                savings = ""

        finance_option = ""
        if item.get("price_monthly"):
            finance_option = f"PAYMENTS AS LOW AS: {self._format_price(item.get('price_monthly'))}/mo"

        image_urls = self._image_urls(item)
        image_1 = image_urls[0] if len(image_urls) > 0 else (item.get("display_image") or "")
        image_2 = image_urls[1] if len(image_urls) > 1 else ""
        image_3 = image_urls[2] if len(image_urls) > 2 else ""

        description = self._description(item.get("inventory_unit_descriptions") or [])
        features = ", ".join(item.get("floorplan_feature") or item.get("feature_list") or [])

        exterior_colors = item.get("exterior_color_name") or item.get("exterior_colors") or []
        if isinstance(exterior_colors, list):
            exterior_color = ", ".join(str(color) for color in exterior_colors if color)
        else:
            exterior_color = str(exterior_colors or "")

        length = item.get("vehicle_body_length")
        length = str(length) if length not in (None, 0, "") else ""

        dry_weight = item.get("dry_weight")
        dry_weight = str(dry_weight) if dry_weight not in (None, 0, "") else ""

        sleeps = item.get("max_sleeping_count")
        sleeps = str(sleeps) if sleeps not in (None, 0, "") else ""

        mileage_value = item.get("odometer")
        mileage_value = str(mileage_value) if mileage_value not in (None, 0, "") else ""
        mileage_unit = "miles" if mileage_value else ""

        special_tag = ""
        custom_label_0 = (item.get("lot_status") or "").strip()

        try:
            sk = hashlib.md5((vin + title + url).encode("utf8")).hexdigest()
        except Exception:
            sk = hashlib.md5(url.encode("utf8")).hexdigest()

        row = {
            "sk": sk,
            "dealership_name": dealership_name,
            "dealer_type": "RV",
            "dealership_address": dealership_address,
            "dealership_phone": dealership_phone,
            "store_code": store_code,
            "dealer_url": "https://rvcountry.com/",
            "cms": "Coast Technology",
            "condition_": condition,
            "year_": year,
            "make": make,
            "model": model,
            "brand": brand,
            "vin": vin,
            "stock_number": stock_number,
            "url": url,
            "msrp": msrp,
            "price": price,
            "savings": savings,
            "finance_option": finance_option,
            "special_tag": special_tag,
            "type_": type_,
            "sub_type": sub_type,
            "location": location,
            "image_url": image_1,
            "image_url_2": image_2,
            "image_url_3": image_3,
            "title": title,
            "description": description,
            "trim": trim,
            "length": length,
            "doors": "",
            "drivetrain": (item.get("driveline_type") or "").strip(),
            "fuel_type": (item.get("fuel_type") or "").strip(),
            "exterior_color": exterior_color,
            "interior_color": "",
            "sleeps": sleeps,
            "seats": "",
            "dry_weight": dry_weight,
            "mileage_value": mileage_value,
            "mileage_unit": mileage_unit,
            "engine": (item.get("engine") or "").strip(),
            "transmission": "",
            "body_style": "",
            "features": features,
            "custom_label_0": custom_label_0,
            "custom_label_1": "",
            "custom_label_2": "",
            "creation_date": self.creation_date,
        }

        try:
            supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
            self.logger.info("Upserted: %s", title)
        except Exception as exc:
            self.logger.error("Supabase error for %s: %s", url, exc)

    @staticmethod
    def _rvcountry_url(urls):
        for candidate in urls:
            if candidate and "rvcountry.com/inventory/" in candidate:
                return candidate
        for candidate in urls:
            if candidate and "rvcountry.com" in candidate:
                return candidate
        return ""

    @staticmethod
    def _format_price(value):
        if value in (None, "", 0):
            return ""
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return str(value)
        if amount.is_integer():
            return f"${int(amount):,}"
        return f"${amount:,.2f}"

    @staticmethod
    def _image_urls(item):
        urls = []
        for image in item.get("images") or []:
            if isinstance(image, dict):
                image_url = image.get("url")
                if image_url:
                    urls.append(image_url)
            elif image:
                urls.append(str(image))
        return urls

    @staticmethod
    def _description(descriptions):
        parts = []
        for block in descriptions:
            if not isinstance(block, dict):
                continue
            heading = (block.get("heading") or "").strip()
            text = (block.get("description") or "").strip()
            if heading and text:
                parts.append(f"{heading}: {text}")
            elif text:
                parts.append(text)
        return " ".join(parts).strip()
