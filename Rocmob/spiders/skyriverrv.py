import scrapy
import hashlib
import json
from datetime import datetime, timezone
from Rocmob.rocmob_cfg import supabase


class SkyriverrvSpider(scrapy.Spider):
    name = "skyriverrv"

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }

    start_urls = ['https://www.skyriverrv.com/api/feeds/vla']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        self.logger.info(f"Connected to API: {response.url}")

        try:
            data = json.loads(response.text)
            vehicles = data.get('@graph') or []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse API response: {e}")
            return

        self.logger.info(f"Found {len(vehicles)} vehicles in the API feed. Processing...")

        for v in vehicles:
            # 1. --- Default/Static Dealership Values ---
            dealership_name = 'Sky River RV'
            dealer_type = 'RV'
            dealer_url = 'https://www.skyriverrv.com/'
            cms = 'API Feed'
            store_code = ''
            dealership_phone = ''
            dealership_address = ''

            # 2. --- Bulletproof Extraction ---
            title = str(v.get('name') or '').strip()
            desc = str(v.get('description') or '').strip()
            url = str(v.get('url') or '').strip()
            vin = str(v.get('vehicleIdentificationNumber') or '').strip()
            model = str(v.get('model') or '').strip()
            year = str(v.get('vehicleModelDate') or '').strip()
            type_ = str(v.get('bodyType') or '').strip()
            Trim = str(v.get('vehicleConfiguration') or '').strip()
            Transmission = str(v.get('vehicleTransmission') or '').strip()
            seats = str(v.get('seatingCapacity') or '').strip()

            # --- Brand handling ---
            brand_data = v.get('brand') or {}
            make = str(brand_data.get('name') or '') if isinstance(brand_data, dict) else str(brand_data or '')
            brand = model

            # --- Offers (Price, Condition, Location) ---
            offers = v.get('offers') or {}
            price = str(offers.get('price') or '').strip()
            if price:
                price = '$' + price

            raw_condition = str(offers.get('itemCondition') or '')
            condition = raw_condition.split('/')[-1].replace('Condition', '')

            # Extract Address & Location safely
            seller = offers.get('seller') or {}
            address = seller.get('address') or {}
            street_address = address.get('streetAddress') or {}

            if isinstance(street_address, dict):
                city = str(street_address.get('city') or '')
                state = str(street_address.get('state') or '')
                zip_code = str(street_address.get('zip') or '')
                street = str(street_address.get('street') or '')
                location = f"{city}, {state}".strip(", ")
                dealership_address = f"{street}, {city}, {state} {zip_code}".strip(", ")
            else:
                location = ''

            # --- Additional Properties (Sleeps, Dry Weight, etc.) ---
            additional_props = v.get('additionalProperty') or []
            sleeps = dry_weight = ''
            for prop in additional_props:
                prop_name = str(prop.get('name') or '')
                prop_val = str(prop.get('value') or '')
                if prop_name == 'Sleeping Capacity':
                    sleeps = prop_val
                elif prop_name == 'Dry Weight':
                    dry_weight = prop_val

            # --- Image Handling ---
            images = v.get('image') or []
            if isinstance(images, str):
                images = [images]

            image_1 = str(images[0]) if len(images) > 0 else ''
            image_2 = str(images[1]) if len(images) > 1 else ''
            image_3 = str(images[2]) if len(images) > 2 else ''

            # --- Blank Variables to match table structure ---
            msrp = savings = Finance_option = Special_Tag = sub_type = ''
            length = Doors = Drivetrain = Fuel_Type = ''
            exterior_color = interior_color = ''
            mileage_value = mileage_unit = engine = body_style = features = ''
            custom_label_0 = custom_label_1 = custom_label_2 = ''
            stock_number = ''

            # 3. --- Generate Hash ---
            try:
                sk = hashlib.md5(vin.encode('utf8') + title.encode('utf8') + url.encode('utf8')).hexdigest()
            except Exception:
                sk = hashlib.md5(str(url).encode('utf8')).hexdigest()

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
                "doors": Doors,
                "drivetrain": Drivetrain,
                "fuel_type": Fuel_Type,
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
                "features": features,
                "custom_label_0": custom_label_0,
                "custom_label_1": custom_label_1,
                "custom_label_2": custom_label_2,
                "creation_date": self.creation_date,
            }

            # One row per (sk, creation_date) per UTC day; same-day re-run updates
            try:
                supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
                self.logger.info(f"Upserted: {title}")
            except Exception as e:
                self.logger.error(f"Supabase error for VIN {vin}: {e}")
