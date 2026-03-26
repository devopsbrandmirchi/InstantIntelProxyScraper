import scrapy
import hashlib
import requests
from datetime import datetime, timezone
from scrapy import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


class RockyridgeSpider(scrapy.Spider):
    name = "rockyridgerv"
    start_urls = ['https://www.google.com']

    inventory_urls = ['https://www.rockyridgerv.com/inventory']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def start_requests(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml',
        }
        for url in self.inventory_urls:
            yield Request(url=url, headers=headers, callback=self.parse, meta={'headers': headers})

    def parse(self, response):
        sel = Selector(response)
        headers = response.meta.get('headers', {})
        urls = sel.xpath('//div[@class="col-xs-12"]//a//@href').extract()

        for i in urls:
            full_url = response.urljoin(i)
            yield Request(url=full_url, callback=self.parse_next, headers=headers, meta={'headers': headers})

        next_page = sel.xpath('//a[@aria-label="Next"]/@href').get()
        if next_page:
            next_url = response.urljoin(next_page)
            yield Request(next_url, callback=self.parse, headers=headers, meta={'headers': headers})

    def parse_next(self, response):
        page_url = response.url
        try:
            resp = requests.get(page_url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.logger.error("Request failed for %s: %s", page_url, e)
            return
        sel = Selector(text=resp.text)
        url = page_url

        dealership_name = 'Rocky Ridge RV'
        dealer_type = 'RV'
        dealership_address = ''
        dealership_phone = ''
        store_code = ''
        dealer_url = 'https://www.rockyridgerv.com/'
        cms = 'Ride Digital'

        Finance_option = Special_Tag = Description = Drivetrain = Fuel_Type = ''
        exterior_color = interior_color = mileage_value = mileage_unit = ''
        engine = Transmission = body_style = ''
        custom_label_0 = custom_label_1 = custom_label_2 = ''
        length = doors = sleeps = dry_weight = seats = ''

        title = ''.join(sel.xpath('//h1//text()').extract())
        msrp = ''.join(sel.xpath('//div[@id="price-msrp"]//div[@class="price-value"]//text()').extract())
        price = ''.join(sel.xpath('//div[@id="price-sale"]//div[@class="price-value"]//text()').extract())
        savings = ''.join(sel.xpath('//div[@id="vdp-savings"]//span//text()').extract())
        images = sel.xpath('//div[@id="gallery-8"]//img//@src').extract()
        image_1 = image_2 = image_3 = ''
        if len(images) >= 3:
            image_1, image_2, image_3 = images[0], images[1], images[2]
        elif len(images) == 2:
            image_1, image_2 = images[0], images[1]
        elif len(images) == 1:
            image_1 = images[0]
        description = ','.join(sel.xpath('//div[@class="widget widget-web-desc"]//text()').extract())
        stock_number = ''.join(sel.xpath('//table//tr[@class="bd-stock"]//td[2]//text()').extract())
        year = ''.join(sel.xpath('//table//tr[@class="bd-year"]//td[2]//text()').extract())
        condition_ = ''.join(sel.xpath('//table//tr[@class="bd-condition"]//td[2]//text()').extract())
        make = ''.join(sel.xpath('//table//tr[@class="bd-make"]//td[2]//text()').extract())
        model = ''.join(sel.xpath('//table//tr[@class="bd-model"]//td[2]//text()').extract())
        brand = model
        trim = ''.join(sel.xpath('//table//tr[@class="bd-trim"]//td[2]//text()').extract())
        location = ''.join(sel.xpath('//table//tr[@class="bd-location"]//td[2]//text()').extract())
        type_ = ''.join(sel.xpath('//table//tr[@class="spec_rds_class"]//td[2]//text()').extract())
        sub_type = ''.join(sel.xpath('//table//tr[@class="spec_secondary_class"]//td[2]//text()').extract())
        interior_color = ''.join(sel.xpath('//table//tr[@class="spec_interior_color"]//td[2]//text()').extract())
        exterior_color = ''.join(sel.xpath('//table//tr[@class="spec_exterior_color"]//td[2]//text()').extract())
        vin = ''.join(sel.xpath('//table//tr[@class="spec_vin"]//td[2]//text()').extract())
        if not vin:
            vin = stock_number
        length = ''.join(sel.xpath('//table//tr[@class="spec_length"]//td[2]//text()').extract()).replace('"', '')
        doors = ''.join(sel.xpath('//table//tr[@class="spec_rds_number_of_doors"]//td[2]//text()').extract())
        sleeps = ''.join(sel.xpath('//table//tr[@class="spec_rds_max_sleeping_count"]//td[2]//text()').extract())
        dry_weight = ''.join(sel.xpath('//table//tr[@class="spec_rds_dry_weight_lbs"]//td[2]//text()').extract()).replace('lbs. LBS', 'lbs')
        engine = ''.join(sel.xpath('//table//tr[@class="spec_engine_model"]//td[2]//text()').extract())
        features = ''.join(sel.xpath('//table//td//strong[contains(text(),"General Features ")]//..//following-sibling::td//text()').extract())
        seats = ''.join(sel.xpath('//table//td//strong[contains(text(),"Seating Capacity ")]//..//following-sibling::td//text()').extract())
        mileage_value = ''.join(sel.xpath('//table//td//strong[contains(text(),"Mileage")]//..//following-sibling::td//text()').extract())
        Finance_option = ''.join(sel.xpath('//div[contains(text(),"FINANCE REBATE")]//span//text()').extract()) or ''.join(sel.xpath('//table//tr[@class="spec_shop_payment"]//td[2]/text()').extract())

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
            "trim": trim,
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
            "features": features,
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
