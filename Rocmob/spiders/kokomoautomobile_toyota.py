import hashlib
import json
import re

import scrapy
from datetime import datetime, timezone
from scrapy.http import Request

from Rocmob.rocmob_cfg import supabase


class KokomoToyotaSpider(scrapy.Spider):
    name = "kokomoautomobiletoyota"
    allowed_domains = ["kokomo-toyota.com"]
    
    # --- PLAYWRIGHT FIX 1: Start at the actual homepage to get the security cookie ---
    start_urls = ["https://www.kokomo-toyota.com/"]

    # --- PLAYWRIGHT FIX 2: Enable the real browser engine ---
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
        super(KokomoToyotaSpider, self).__init__(*args, **kwargs)
        self.base_url = "https://www.kokomo-toyota.com/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory"
        self.page_size = 162
        
        # Supabase specific fields
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
        self.inserted_count = 0

    # --- PLAYWRIGHT FIX 3: Open the browser and lock in a session ---
    def start_requests(self):
        self.logger.info("🚀 Starting Kokomo Toyota Spider...")
        for url in self.start_urls:
            self.logger.info(f"🌐 Navigating to homepage to grab security cookies 🍪...")
            yield Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_context": "toyota_session", # This keeps the cookie alive
                },
                callback=self.parse
            )

    def parse(self, response):
        self.logger.info("🎭 Playwright successfully bypassed security! Real cookies acquired. Fetching API 📦...")
        yield self.make_request(0)

    def make_request(self, page_start):
        url = f"{self.base_url}?pageStart={page_start}&pageSize={self.page_size}"
        self.logger.info(f"📡 Requesting API Page Start: {page_start}...")
        
        # --- PLAYWRIGHT FIX 4: Use the same browser session for the API call ---
        return Request(
            url=url, 
            callback=self.parse_inventory, 
            dont_filter=True,
            meta={
                'page_start': page_start,
                "playwright": True,
                "playwright_context": "toyota_session"
            }
        )

    def parse_inventory(self, response):
        vehicles = []
        total_count = 0
        current_start = 0

        try:
            # --- PLAYWRIGHT FIX 5: Safely extract JSON if Playwright wraps it in HTML ---
            raw_text = response.css('pre::text').get() or response.text
            json_data = json.loads(raw_text)
            
            page_info = json_data.get("pageInfo", {})
            total_count = page_info.get("totalCount", 0)
            vehicles = page_info.get("trackingData", [])
            
            server_page_start = page_info.get("pageStart", 0)
            requested_start = response.meta.get("page_start", 0)

            self.logger.info(f"📊 API Response: {len(vehicles)} vehicles found in this batch (Target Total: {total_count}).")

            # DUPLICATE PROTECTION
            if requested_start != 0 and server_page_start == 0:
                self.logger.warning("🛑 Server reset pageStart to 0. Stopping pagination to avoid infinite loops.")
                return

            for index, vehicle in enumerate(vehicles):
                try:
                    # --- 1. EXTRACT DATA ---
                    year = vehicle.get("modelYear", "")
                    make = vehicle.get("make", "")
                    model = vehicle.get("model", "")
                    stock_no = vehicle.get("stockNumber", "")
                    vin = vehicle.get("vin", "")
                    link = vehicle.get("link", "")
                    
                    # --- 2. CRITICAL FIX: FIND MISSING VIN IN LINK ---
                    if not vin and link:
                        match = re.search(r'[A-HJ-NPR-Z0-9]{17}', link.upper())
                        if match:
                            vin = match.group(0)
                            self.logger.info(f"🕵️‍♂️ Recovered missing VIN from link URL: {vin}")

                    # --- 3. GENERATE UNIQUE ID (SK) ---
                    title = f"{year} {make} {model}".strip()
                    if link and not str(link).startswith("http"):
                        link = f"https://www.kokomo-toyota.com{link}"

                    unique_string = f"{vin}{stock_no}{title}{response.url}{index}"
                    sk = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

                    # --- 4. FINAL FALLBACK FOR VIN ---
                    if not vin:
                        vin = f"TEMP-{stock_no if stock_no else sk[:10]}"
                        self.logger.warning(f"⚠️ VIN completely missing! Using TEMP VIN: {vin}")

                    dealership_name = 'Kokomo Auto World Toyota'
                    dealer_type = 'Auto'
                    cms = 'Dealer.com'
                    dealer_url = 'https://www.kokomo-toyota.com/'

                    brand = model
                    Trim = vehicle.get("trim", "")
                    body_style = vehicle.get("bodyStyle", "")
                    doors = vehicle.get("doors", "")
                    drive_line = vehicle.get("driveLine", "")
                    engine = vehicle.get("engine", "") or ""
                    engine_size = vehicle.get("engineSize", "") or ""
                    if engine_size:
                        engine = f"{engine} {engine_size}".strip()
                    Transmission = vehicle.get("transmission", "")
                    fuel_type = vehicle.get("fuelType", "")
                    exterior_color = vehicle.get("exteriorColor", "")
                    interior_color = vehicle.get("interiorColor", "")
                    odometer = vehicle.get("odometer", "")
                    condition_ = vehicle.get("newOrUsed", "")
                    location = ''
                    msrp = vehicle.get("msrp", "")
                    price = vehicle.get("salePrice", "")
                    savings = ''
                    internet_price = vehicle.get("internetPrice", "")
                    
                    raw_images = vehicle.get("images") or []
                    image_1 = image_2 = image_3 = ""
                    if len(raw_images) > 0 and isinstance(raw_images[0], dict):
                        image_1 = raw_images[0].get("uri") or ""
                    if len(raw_images) > 1 and isinstance(raw_images[1], dict):
                        image_2 = raw_images[1].get("uri") or ""
                    if len(raw_images) > 2 and isinstance(raw_images[2], dict):
                        image_3 = raw_images[2].get("uri") or ""

                    # Initialize empty fields for things not provided by the API
                    dealership_address = dealership_phone = store_code = ''
                    Finance_option = Special_Tag = type_ = sub_type = ''
                    Features = custom_label_1 = custom_label_2 = description = ''
                    sleeps = seats = dry_weight = mileage_unit = ''
                    custom_label_0 = internet_price or ""
                    mileage_value = odometer if odometer is not None else ""
                    if mileage_value != "":
                        mileage_value = str(mileage_value)
                    length = ''

                    # --- 5. SUPABASE DICTIONARY FORMAT ---
                    row = {
                        "sk": sk,
                        "dealership_name": dealership_name,
                        "dealer_type": dealer_type,
                        "dealership_address": dealership_address,
                        "dealership_phone": dealership_phone,
                        "store_code": store_code,
                        "dealer_url": dealer_url,
                        "cms": cms,
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
                        "description": description,
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
                    
                    # --- 6. SUPABASE UPSERT ---
                    try:
                        supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
                        self.logger.info(f"🚘 [{index+1}/{len(vehicles)}] Upserted to Supabase: {title} | VIN: {vin}")
                        self.inserted_count += 1
                    except Exception as db_err:
                        self.logger.error(f"❌ Supabase insert failed for {title}: {db_err}")
                
                except Exception as car_err:
                    self.logger.error(f"🔥 Error parsing vehicle data at index {index}: {car_err}")
                    continue

            # --- PAGINATION ---
            items_received = len(vehicles)
            next_start = requested_start + items_received
            
            if items_received > 0 and next_start < total_count:
                self.logger.info(f"⏭️ Moving to next page. Next start index: {next_start}...")
                yield self.make_request(next_start)
            else:
                self.logger.info(f"🎉 Scraping Complete! Total records inserted to Supabase: {self.inserted_count}")

        except Exception as e:
            self.logger.error(f"💀 Critical Error parsing JSON response: {e}")