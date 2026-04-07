import hashlib
import json
import re

import scrapy
from datetime import datetime, timezone
from scrapy.http import Request

from Rocmob.rocmob_cfg import supabase

class KokomoHondaSpider(scrapy.Spider):
    name = "kokomoautomobilehonda"
    allowed_domains = ["kokomohonda.com"]
    start_urls = ["https://www.kokomohonda.com/"] 

    # --- PLAYWRIGHT SETTINGS ---
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        "ENABLE_PROXY": False,
    }

    def __init__(self, *args, **kwargs):
        super(KokomoHondaSpider, self).__init__(*args, **kwargs)
        
        self.base_url = "https://www.kokomohonda.com/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory"
        self.page_size = 162
        self.total_processed = 0
        self.total_count = None
        
        # Supabase specific fields
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
        self.inserted_count = 0

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_context": "honda_session", 
                },
                callback=self.parse
            )

    def parse(self, response):
        self.logger.info("✅ Homepage loaded via Playwright! Real cookies acquired. Fetching API...")
        yield self.make_request(0)

    def make_request(self, page_start):
        url = f"{self.base_url}?pageStart={page_start}&pageSize={self.page_size}"
        return Request(
            url=url,
            callback=self.parse_inventory,
            dont_filter=True,
            meta={
                'page_start': page_start,
                "playwright": True,
                "playwright_context": "honda_session" 
            }
        )

    def parse_inventory(self, response):
        try:
            raw_text = response.css('pre::text').get() or response.text
            
            try:
                json_data = json.loads(raw_text)
            except json.JSONDecodeError as json_err:
                self.logger.error(f"❌ JSON decode error: {json_err}")
                return
            
            page_info = json_data.get("pageInfo", {})
            if not page_info:
                return
            
            total_count = page_info.get("totalCount", 0)
            vehicles = page_info.get("trackingData", [])
            current_start = page_info.get("pageStart", 0)
            
            if self.total_count is None:
                self.total_count = total_count
            
            if not vehicles or self.total_processed >= self.total_count:
                return

            remaining_needed = self.total_count - self.total_processed
            vehicles_to_process = min(len(vehicles), remaining_needed) if remaining_needed > 0 else len(vehicles)

            for idx, vehicle in enumerate(vehicles):
                if self.total_processed >= self.total_count or idx >= vehicles_to_process:
                    break
                
                try:
                    self.total_processed += 1
                    
                    dealership_name = 'Kokomo Auto World Honda'
                    dealer_type = 'Auto'
                    cms = 'Dealer.com'
                    dealer_url = 'https://www.kokomohonda.com/'
                    
                    vin = vehicle.get("vin", "") or ""
                    year = vehicle.get("modelYear", "") or ""
                    make = vehicle.get("make", "") or ""
                    model = vehicle.get("model", "") or ""
                    raw_link = vehicle.get("link", "") or ""
                    stock_number = vehicle.get("stockNumber", "") or ""
                    url = f"https://www.kokomohonda.com{raw_link}" if raw_link else ""
                    if not vin and raw_link:
                        m = re.search(r"[A-HJ-NPR-Z0-9]{17}", raw_link.upper())
                        if m:
                            vin = m.group(0)
                    title = f"{year} {make} {model}".strip()
                    if not vin:
                        vin = f"TEMP-{stock_number or hashlib.md5((title + url + response.url).encode()).hexdigest()[:10]}"
                        self.logger.warning("Kokomo Honda: missing VIN; using %s", vin)

                    sk = hashlib.md5((vin + title + url).encode("utf-8")).hexdigest()

                    brand = model
                    Trim = vehicle.get("trim", "") or ""
                    body_style = vehicle.get("bodyStyle", "") or ""
                    doors = vehicle.get("doors", "") or ""
                    drive_line = vehicle.get("driveLine", "") or ""
                    engine = vehicle.get("engine", "") or ""
                    engine_size = vehicle.get("engineSize", "") or ""
                    if engine_size:
                        engine = f"{engine} {engine_size}".strip()
                    Transmission = vehicle.get("transmission", "") or ""
                    fuel_type = vehicle.get("fuelType", "") or ""
                    exterior_color = vehicle.get("exteriorColor", "") or ""
                    interior_color = vehicle.get("interiorColor", "") or ""
                    condition = vehicle.get("newOrUsed", "") or ""
                    
                    msrp = vehicle.get("msrp", "") or ""
                    price = vehicle.get("salePrice", "") or ""
                    internet_price = vehicle.get("internetPrice", "") or ""
                    odometer = vehicle.get("odometer", "") or ""

                    images = vehicle.get("images", []) or []
                    image_1 = images[0].get("uri") if len(images) > 0 and isinstance(images[0], dict) else ""
                    image_2 = images[1].get("uri") if len(images) > 1 and isinstance(images[1], dict) else ""
                    image_3 = images[2].get("uri") if len(images) > 2 and isinstance(images[2], dict) else ""

                    # Initialize empty fields for things not provided by the API
                    dealership_address = dealership_phone = store_code = ''
                    Finance_option = Special_Tag = type_ = sub_type = location = savings = ''
                    Features = custom_label_1 = custom_label_2 = desc = ''
                    sleeps = seats = dry_weight = mileage_unit = ''
                    custom_label_0 = internet_price
                    mileage_value = odometer
                    length = ''

                    # --- SUPABASE DICTIONARY ---
                    row = {
                        "sk": sk,
                        "dealership_name": dealership_name,
                        "dealer_type": dealer_type,
                        "dealership_address": dealership_address,
                        "dealership_phone": dealership_phone,
                        "store_code": store_code,
                        "dealer_url": dealer_url,
                        "cms": cms,
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
                        "finance_option": Finance_option,
                        "special_tag": Special_Tag,
                        "type_": type_,
                        "sub_type": sub_type,
                        "location": location,
                        "image_url": image_1,
                        "image_url_2": image_2,
                        "image_url_3": image_3,
                        "title": title,
                        "description": desc,
                        "trim": Trim,
                        "length": length,
                        "doors": doors,
                        "drivetrain": drive_line,
                        "fuel_type": fuel_type,
                        "exterior_color": exterior_color,
                        "interior_color": interior_color,
                        "sleeps": sleeps,
                        "seats": seats,
                        "dry_weight": dry_weight,
                        "mileage_value": mileage_value,
                        "mileage_unit": mileage_unit,
                        "engine": engine,
                        "transmission": Transmission,
                        "body_style": body_style,
                        "features": Features,
                        "custom_label_0": custom_label_0,
                        "custom_label_1": custom_label_1,
                        "custom_label_2": custom_label_2,
                        "creation_date": self.creation_date,
                    }

                    # --- SUPABASE UPSERT LOGIC ---
                    try:
                        supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
                        self.logger.info("Upserted: %s", title)
                    except Exception as e:
                        self.logger.error("Supabase error for %s: %s", url, e)
                    
                    print(f"Records inserted so far: {self.inserted_count + 1}")
                    self.inserted_count += 1
                
                except Exception as vehicle_err:
                    self.logger.error(f"❌ Error processing vehicle {idx + 1}: {vehicle_err}")
                    continue

            # --- PAGINATION LOGIC ---
            try:
                vehicles_returned = len(vehicles)
                next_start = current_start + vehicles_returned
                
                if self.total_processed >= self.total_count:
                    self.logger.info(f"✅ Reached target count: {self.total_processed}/{self.total_count}, stopping pagination")
                    return
                
                if next_start < total_count and vehicles_returned > 0:
                    remaining = self.total_count - self.total_processed
                    if remaining > 0:
                        yield self.make_request(next_start)
                    else:
                        self.logger.info("✅ All vehicles processed.")
            except Exception as pagination_err:
                self.logger.error(f"❌ Error in pagination: {pagination_err}")

        except Exception as e:
            self.logger.error(f"❌ Error parsing inventory: {e}")