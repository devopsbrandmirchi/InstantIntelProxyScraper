import scrapy
import hashlib
import json
from datetime import datetime, timezone
from scrapy.http import JsonRequest
from Rocmob.rocmob_cfg import supabase


class CampingworldLitSpider(scrapy.Spider):
    name = "campingworldareaLIT"
    allowed_domains = ["campingworld.com", "algolianet.com"]
    inventory_url = "https://rv.campingworld.com/shop-rvs?indexName=rvcw-inventory_recommended&glCode=lit"

    api_key = '93b5c9bc66306b3f4c39c79e292dfb5d'
    app_id = 'QASGLULENW'
    api_url_template = "https://qasglulenw-3.algolianet.com/1/indexes/*/queries"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def start_requests(self):
        yield scrapy.Request(
            url=self.inventory_url,
            callback=self.get_api_key,
            errback=self.handle_error,
            meta={"playwright": True},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
        )

    def get_api_key(self, response):
        try:
            self.api_url = self.api_url_template
            self.custom_headers = {
                "Content-Type": "application/json",
                "X-Algolia-API-Key": self.api_key,
                "X-Algolia-Application-Id": self.app_id,
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://rv.campingworld.com",
                "Referer": self.inventory_url
            }
            yield self.make_request(page=0)
        except Exception as e:
            self.logger.error("Error in get_api_key: %s", e)

    def make_request(self, page):
        payload = {
            "requests": [
                {
                    "indexName": "rvcw-inventory_recommended",
                    "params": "query=&hitsPerPage=20&page={}&facetFilters=[[\"glCode:lit\"]]".format(page)
                }
            ]
        }
        return JsonRequest(
            url=self.api_url,
            headers=self.custom_headers,
            data=payload,
            callback=self.parse_results,
            errback=self.handle_error,
            meta={'page': page}
        )

    def parse_results(self, response):
        self.parse_next(response.text)
        try:
            data = response.json()
            page_info = data['results'][0]['page']
            nb_pages = data['results'][0]['nbPages']
            if page_info + 1 < nb_pages:
                yield self.make_request(page_info + 1)
        except (KeyError, IndexError, TypeError) as e:
            self.logger.error("Error parsing results: %s", e)

    def parse_next(self, raw_json_text):
        try:
            data = json.loads(raw_json_text)
            hits = data.get('results', [{}])[0].get('hits', [])
            for item in hits:
                dealership_name = 'Camping World (North Little Rock, AR)'
                dealer_type = 'RV'
                cms = ''
                Finance_option = Special_Tag = Doors = Drivetrain = Fuel_Type = ''
                exterior_color = interior_color = seats = mileage_value = mileage_unit = ''
                sleeps = Transmission = body_style = ''
                custom_label_0 = custom_label_1 = custom_label_2 = ''
                Features = engine = description = length = dry_weight = ''

                dealer_url = 'https://rv.campingworld.com/rv/'
                store_code = dealership_phone = dealership_address = ''

                title = item.get('assetSlug', '') or ''
                url = "https://rv.campingworld.com/rv/" + title

                condition_ = item.get('condition', '') or ''
                year = item.get('year', '')
                if year == 0:
                    year = ''
                year = str(year) if year else ''

                make = item.get('make', '') or ''
                model = item.get('brand', '') or ''
                brand = model
                type_ = item.get('classDisplay', '') or ''
                sub_type = ''
                Trim = item.get('model', '') or ''
                location = (item.get('dealer') or {}).get('locationName', '') or ''
                vin = (item.get('chassisNumber', '') or '').upper()
                stock_number = item.get('stockNumber', '') or ''

                msrp = ''
                price = "$" + str(item.get('publishedPrice', '')) if item.get('publishedPrice') else ''
                savings = ''
                Finance_option = "$" + str(item.get('monthlyPayment', '')) if item.get('monthlyPayment') else ''

                image_1 = (item.get('images') or {}).get('imageUrl', '') or ''
                image_2 = item.get('productFloorplanImageUrl', '') or ''
                image_3 = ''

                try:
                    sk = hashlib.md5((str(vin) + str(title) + url).encode("utf8")).hexdigest()
                except Exception:
                    sk = hashlib.md5(url.encode("utf8")).hexdigest()

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
                    "description": description,
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
                    "features": Features,
                    "custom_label_0": custom_label_0,
                    "custom_label_1": custom_label_1,
                    "custom_label_2": custom_label_2,
                    "creation_date": self.creation_date,
                }

                try:
                    supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
                    self.logger.info("Upserted: %s", title)
                except Exception as db_err:
                    self.logger.error("Supabase error for %s: %s", url, db_err)

        except Exception as e:
            self.logger.error("Failed in parse_next: %s", e)

    def handle_error(self, failure):
        self.logger.error("Request failed: %s", failure)
