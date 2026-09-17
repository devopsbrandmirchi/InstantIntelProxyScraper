import hashlib
import json
from datetime import datetime, timezone

import scrapy

from Rocmob.rocmob_cfg import supabase


class SkyriverrvSpider(scrapy.Spider):
    name = "skyriverrv"

    custom_settings = {
        "ENABLE_PROXY": False,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
    }

    start_urls = ["https://www.skyriverrv.com/api/feeds/vla"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        self.logger.info("Connected to API: %s", response.url)

        try:
            data = json.loads(response.text)
            vehicles = data.get("@graph") or []
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse API response: %s", exc)
            return

        self.logger.info("Found %s vehicles in the API feed. Processing...", len(vehicles))

        for v in vehicles:
            dealership_name = "Sky River RV"
            dealer_type = "RV"
            dealer_url = "https://www.skyriverrv.com/"
            cms = "API Feed"
            store_code = ""
            dealership_phone = ""

            title = str(v.get("name") or "").strip()
            desc = str(v.get("description") or "").strip()
            url = str(v.get("url") or "").strip()
            vin = str(v.get("vehicleIdentificationNumber") or "").strip()
            model = str(v.get("model") or "").strip()
            year = str(v.get("vehicleModelDate") or "").strip()
            type_ = str(v.get("bodyType") or "").strip()
            trim = str(v.get("vehicleConfiguration") or "").strip()
            transmission = str(v.get("vehicleTransmission") or "").strip()
            seats = str(v.get("seatingCapacity") or "").strip()

            brand_data = v.get("brand") or {}
            make = (
                str(brand_data.get("name") or "")
                if isinstance(brand_data, dict)
                else str(brand_data or "")
            )
            brand = model

            offers = v.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                offers = {}

            price = str(offers.get("price") or "").strip()
            if price and not price.startswith("$"):
                price = "$" + price

            raw_condition = str(offers.get("itemCondition") or "")
            condition = raw_condition.split("/")[-1].replace("Condition", "")

            seller = offers.get("seller") or {}
            if isinstance(seller, list):
                seller = seller[0] if seller else {}
            if not isinstance(seller, dict):
                seller = {}
            address = seller.get("address") or {}
            if isinstance(address, list):
                address = address[0] if address else {}
            if not isinstance(address, dict):
                address = {}

            street = str(address.get("streetAddress") or "").strip()
            city = str(address.get("addressLocality") or "").strip()
            state = str(address.get("addressRegion") or "").strip()
            zip_code = str(address.get("postalCode") or "").strip()
            # Older feed shape: streetAddress was a nested dict
            street_nested = address.get("streetAddress")
            if isinstance(street_nested, dict):
                street = str(street_nested.get("street") or "").strip()
                city = str(street_nested.get("city") or city).strip()
                state = str(street_nested.get("state") or state).strip()
                zip_code = str(street_nested.get("zip") or zip_code).strip()

            location = f"{city}, {state}".strip(", ")
            dealership_address = f"{street}, {city}, {state} {zip_code}".strip(", ")

            additional_props = v.get("additionalProperty") or []
            if isinstance(additional_props, dict):
                additional_props = [additional_props]
            sleeps = dry_weight = ""
            for prop in additional_props:
                if not isinstance(prop, dict):
                    continue
                prop_name = str(prop.get("name") or "")
                prop_val = str(prop.get("value") or "")
                if prop_name == "Sleeping Capacity":
                    sleeps = prop_val
                elif prop_name == "Dry Weight":
                    dry_weight = prop_val

            images = v.get("image") or []
            if isinstance(images, str):
                images = [images]
            image_1 = str(images[0]) if len(images) > 0 else ""
            image_2 = str(images[1]) if len(images) > 1 else ""
            image_3 = str(images[2]) if len(images) > 2 else ""

            msrp = savings = finance_option = special_tag = sub_type = ""
            length = doors = drivetrain = fuel_type = ""
            exterior_color = interior_color = ""
            mileage_value = mileage_unit = engine = body_style = features = ""
            custom_label_0 = custom_label_1 = custom_label_2 = ""
            stock_number = ""

            try:
                sk = hashlib.md5(
                    vin.encode("utf8") + title.encode("utf8") + url.encode("utf8")
                ).hexdigest()
            except Exception:
                sk = hashlib.md5(str(url).encode("utf8")).hexdigest()

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
                "finance_option": finance_option,
                "special_tag": special_tag,
                "type_": type_,
                "sub_type": sub_type,
                "location": location,
                "image_url": image_1,
                "image_url_2": image_2,
                "image_url_3": image_3,
                "title": title,
                "description": desc,
                "trim": trim,
                "length": length,
                "doors": doors,
                "drivetrain": drivetrain,
                "fuel_type": fuel_type,
                "exterior_color": exterior_color,
                "interior_color": interior_color,
                "sleeps": sleeps,
                "seats": seats,
                "dry_weight": dry_weight,
                "mileage_value": mileage_value,
                "mileage_unit": mileage_unit,
                "engine": engine,
                "transmission": transmission,
                "body_style": body_style,
                "features": features,
                "custom_label_0": custom_label_0,
                "custom_label_1": custom_label_1,
                "custom_label_2": custom_label_2,
                "creation_date": self.creation_date,
            }

            try:
                supabase.table("scrap_rawdata").upsert(
                    row, on_conflict="sk,creation_date"
                ).execute()
                self.logger.info("Upserted: %s", title)
            except Exception as exc:
                self.logger.error("Supabase error for VIN %s: %s", vin, exc)
