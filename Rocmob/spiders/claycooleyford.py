import scrapy
import hashlib
import json
from datetime import datetime, timezone
from scrapy.selector import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


class ClaycooleyfordSpider(scrapy.Spider):
    name = "claycooleyford"
    start_urls = ['https://www.claycooleyford.com/inventoryvdpsitemap.xml']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        data = response.text
        sel = Selector(text=data.replace('\r', '').replace('\n', ''))
        urls = sel.xpath('//url//loc//text()').extract()
        for url in urls:
            type_ = ""
            vin = ""
            if '/used/' in url:
                type_ = "Used"
                vin = url.split('/used/')[-1].split('/')[0]
            elif "/new/" in url:
                type_ = "New"
                vin = url.split('/new/')[-1].split('/')[0]
            else:
                continue
            if url:
                api_url = 'https://www.claycooleyford.com/api/Inventory/vehicle?vin=%s&accountid=75671' % (vin,)
                yield Request(url, callback=self.parse_html, meta={'type_': type_, "url": url, "api_url": api_url})

    def parse_html(self, response):
        sel = Selector(response)
        api_url = response.meta.get('api_url', '')
        type_ = response.meta.get('type_', '')
        title = ''.join(sel.xpath('//div[@class="oem-vehicle-title-section"]//h1//text()').extract()).strip()
        location = ''.join(sel.xpath('//div[@class="cursor-pointer header-dealer-address"]//text()').extract()).strip()
        yield Request(
            api_url,
            callback=self.parse_next,
            meta={'type_': type_, "url": response.url, "api_url": api_url, "title": title, 'location': location}
        )

    def parse_next(self, response):
        data = json.loads(response.text)
        url = response.meta.get('url', '')
        title = response.meta.get('title', '')

        dealership_name = 'Clay Cooley Ford'
        dealership_phone = ''
        dealer_type = 'Auto'
        dealership_address = "633 N. Watson Rd Arlington, TX 76011"
        store_code = ''
        dealer_url = 'https://www.claycooleyford.com/'
        cms = 'Interact RV'

        Finance_option = Special_Tag = Trim = length = dry_weight = sleeps = ''
        Doors = Drivetrain = Fuel_Type = exterior_color = interior_color = ''
        seats = mileage_value = mileage_unit = sub_type = ''
        custom_label_0 = custom_label_1 = custom_label_2 = ''

        sub_cat = data.get('subcategories', '') or []
        Features = []
        for cat_name in sub_cat:
            features_name = cat_name.get('subCatName', '')
            Features.append(features_name)
        features_str = ', '.join(Features) if isinstance(Features, list) else str(Features or '')

        year = data.get('year', '') or ''
        condition_ = response.meta.get('type_', '')
        desc = data.get('description', '') or ''
        vin = data.get('vin', '') or ''
        stock_number = data.get('stock', '') or ''
        if not vin:
            vin = stock_number

        all_price_list = data.get('buyFors', '') or []
        msrp = price = savings = ''
        if all_price_list:
            for all_price in all_price_list:
                msrp = all_price.get('msrp', '')
                price = all_price.get('buyForPrice', '')
                savings = all_price.get('discount', '')
        else:
            msrp = data.get('msrp', '')
            price = data.get('sellingPrice', '')
        if msrp != '' and price != '' and savings == '':
            try:
                m = float(str(msrp).replace('$', '').replace(',', '')) if msrp else 0
                p = float(str(price).replace('$', '').replace(',', '')) if price else 0
                savings = m - p
            except (TypeError, ValueError):
                savings = ''
        if savings == 0 or savings == '0':
            savings = ''

        type_ = data.get('body', '') or ''
        location = 'Arlington, TX'
        body_style = data.get('body', '') or ''
        exterior_color = data.get('exteriorColor', '') or ''
        interior_color = data.get('interiorColor', '') or ''
        Transmission = data.get('transmission', '') or ''
        engine = data.get('engine_Description', '') or ''
        Fuel_Type = data.get('fuel_Type', '') or ''
        Trim = data.get('trim', '') or ''
        brand = title.split(' ')[1] if len(title.split()) > 1 else ''
        model = data.get('model', '') or ''
        make = data.get('make', '') or ''
        doors = data.get('doors', '') or ''
        if isinstance(doors, (int, float)):
            doors = str(doors)

        image_urls = data.get('photoURLs') or ''
        if image_urls:
            images = image_urls.split(',') if isinstance(image_urls, str) else image_urls
        else:
            images = []
        image_1 = image_2 = image_3 = ''
        if len(images) >= 3:
            image_1, image_2, image_3 = images[0], images[1], images[2]
        elif len(images) == 2:
            image_1, image_2 = images[0], images[1]
        elif len(images) == 1:
            image_1 = images[0]
            if image_1 and 'no-image-generic' in image_1:
                image_1 = ''

        try:
            sk = hashlib.md5(vin.encode('utf8') + title.encode('utf8') + url.encode('utf8')).hexdigest()
        except Exception:
            sk = hashlib.md5(url.encode('utf8')).hexdigest()

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
            "year_": str(year),
            "make": str(make),
            "model": str(model),
            "brand": str(brand),
            "vin": str(vin),
            "stock_number": str(stock_number),
            "url": url,
            "msrp": str(msrp) if msrp else '',
            "price": str(price) if price else '',
            "savings": str(savings) if savings else '',
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
            "features": features_str,
            "custom_label_0": custom_label_0,
            "custom_label_1": custom_label_1,
            "custom_label_2": custom_label_2,
            "creation_date": self.creation_date,
        }

        try:
            supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
            self.logger.info("Upserted: %s", title)
        except Exception as e:
            self.logger.error("Supabase error for %s: %s", url, e)
