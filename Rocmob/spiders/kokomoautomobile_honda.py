import hashlib
import json
import re

import scrapy
from datetime import datetime, timezone
from scrapy.http import Request

from Rocmob.rocmob_cfg import supabase


def _s(val):
    return "" if val is None else str(val)


class KokomoHondaSpider(scrapy.Spider):
    name = "kokomoautomobilehonda"
    allowed_domains = ["kokomohonda.com"]

    custom_settings = {
        "ENABLE_PROXY": True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
        self.base_url = (
            "https://www.kokomohonda.com/apis/widget/"
            "INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory"
        )
        self.page_size = 162
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.kokomohonda.com/",
            "Origin": "https://www.kokomohonda.com",
            "X-Requested-With": "XMLHttpRequest",
        }

    def start_requests(self):
        # Do not use google.com as bootstrap — Bright Data blocks SERP domains.
        yield self.make_request(0)

    def make_request(self, page_start):
        url = f"{self.base_url}?pageStart={page_start}&pageSize={self.page_size}"
        return Request(
            url=url,
            headers=self.headers,
            callback=self.parse_inventory,
            meta={"page_start": page_start},
        )

    def parse_inventory(self, response):
        try:
            json_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error("Kokomo Honda: invalid JSON: %s", e)
            return

        page_info = json_data.get("pageInfo") or {}
        if not page_info:
            self.logger.warning("Kokomo Honda: no pageInfo in response")
            return

        total_count = page_info.get("totalCount", 0)
        vehicles = page_info.get("trackingData") or []
        server_page_start = page_info.get("pageStart", 0)
        requested_start = response.meta.get("page_start", 0)

        if requested_start != 0 and server_page_start == 0:
            self.logger.info("Kokomo Honda: server reset pageStart to 0; stopping pagination.")
            return

        dealer_url = "https://www.kokomohonda.com/"
        dealership_name = "Kokomo Auto World Honda"

        for vehicle in vehicles:
            try:
                row = self._vehicle_to_row(
                    vehicle, response.url, dealer_url, dealership_name
                )
                if not row:
                    continue
                supabase.table("scrap_rawdata").upsert(
                    row, on_conflict="sk,creation_date"
                ).execute()
                self.logger.info("Upserted: %s", row.get("title", ""))
            except Exception as e:
                self.logger.error("Kokomo Honda upsert error: %s", e)

        items_received = len(vehicles)
        next_start = requested_start + items_received
        if items_received > 0 and next_start < total_count:
            yield self.make_request(next_start)

    def _vehicle_to_row(self, vehicle, response_url, dealer_url, dealership_name):
        vin = _s(vehicle.get("vin"))
        year = _s(vehicle.get("modelYear"))
        make = _s(vehicle.get("make"))
        model = _s(vehicle.get("model"))
        stock_no = _s(vehicle.get("stockNumber"))
        link = _s(vehicle.get("link"))

        if link and not link.startswith("http"):
            link = f"https://www.kokomohonda.com{link}"

        if not vin and link:
            match = re.search(r"[A-HJ-NPR-Z0-9]{17}", link.upper())
            if match:
                vin = match.group(0)

        title = f"{year} {make} {model}".strip()

        if not vin:
            vin = f"TEMP-{stock_no if stock_no else hashlib.md5((title + link + response_url).encode()).hexdigest()[:10]}"
            self.logger.warning("Kokomo Honda: missing VIN; using %s", vin)

        sk = hashlib.md5((vin + title + link).encode("utf-8")).hexdigest()

        trim = _s(vehicle.get("trim"))
        body_style = _s(vehicle.get("bodyStyle"))
        doors = _s(vehicle.get("doors"))
        drive_line = _s(vehicle.get("driveLine"))
        engine = _s(vehicle.get("engine"))
        engine_size = _s(vehicle.get("engineSize"))
        if engine_size:
            engine = f"{engine} {engine_size}".strip()
        transmission = _s(vehicle.get("transmission"))
        fuel_type = _s(vehicle.get("fuelType"))
        exterior_color = _s(vehicle.get("exteriorColor"))
        interior_color = _s(vehicle.get("interiorColor"))
        odometer = _s(vehicle.get("odometer"))
        condition_ = _s(vehicle.get("newOrUsed"))
        msrp = _s(vehicle.get("msrp"))
        price = _s(vehicle.get("salePrice"))
        internet_price = _s(vehicle.get("internetPrice"))

        images = vehicle.get("images") or []
        image_1 = image_2 = image_3 = ""
        if len(images) > 0 and isinstance(images[0], dict):
            image_1 = _s(images[0].get("uri"))
        if len(images) > 1 and isinstance(images[1], dict):
            image_2 = _s(images[1].get("uri"))
        if len(images) > 2 and isinstance(images[2], dict):
            image_3 = _s(images[2].get("uri"))

        brand = model

        return {
            "sk": sk,
            "dealership_name": dealership_name,
            "dealer_type": "Auto",
            "dealership_address": "",
            "dealership_phone": "",
            "store_code": "",
            "dealer_url": dealer_url,
            "cms": "Dealer.com",
            "condition_": condition_,
            "year_": year,
            "make": make,
            "model": model,
            "brand": brand,
            "vin": vin,
            "stock_number": stock_no,
            "url": link,
            "msrp": msrp,
            "price": price,
            "savings": "",
            "finance_option": "",
            "special_tag": "",
            "type_": "",
            "sub_type": "",
            "location": "",
            "image_url": image_1,
            "image_url_2": image_2,
            "image_url_3": image_3,
            "title": title,
            "description": "",
            "trim": trim,
            "length": "",
            "doors": doors,
            "drivetrain": drive_line,
            "fuel_type": fuel_type,
            "exterior_color": exterior_color,
            "interior_color": interior_color,
            "sleeps": "",
            "seats": "",
            "dry_weight": "",
            "mileage_value": odometer,
            "mileage_unit": "",
            "engine": engine,
            "transmission": transmission,
            "body_style": body_style,
            "features": "",
            "custom_label_0": internet_price,
            "custom_label_1": "",
            "custom_label_2": "",
            "creation_date": self.creation_date,
        }
