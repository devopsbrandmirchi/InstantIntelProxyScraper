import scrapy
import re
import hashlib
import json
from datetime import datetime, timezone
from scrapy.http import Request
from scrapy import Selector
from Rocmob.rocmob_cfg import supabase


class Rohrmantoyota(scrapy.Spider):
    name = "rohrmantoyota"
    start_urls = ['https://www.rohrmantoyota.com/searchall.aspx']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # UTC date for this crawl (matches cron / daily snapshot)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        sel = Selector(response)
        data = ''.join(sel.xpath('//script[@id="dealeron_tagging_data"]//text()').extract())
        json_data = json.loads(data)
        items = json_data['items']
        for item in items:
            url = 'https://www.rohrmantoyota.com/used-Lafayette-2022-Ford-Escape-SE-{}'.format(item)
            yield Request(url, callback=self.parse_next, meta={'type_url': response.url})
        next_page = ''.join(sel.xpath('//link[@rel="next"]/@href').extract())
        if next_page:
            next_link = 'https:' + next_page
            print(next_link)
            yield Request(next_link, callback=self.parse)

    def parse_next(self, response):
        sel = Selector(response)
        features = Finance_option = Special_Tag = length = Doors = Drivetrain = ''
        sleeps = seats = dry_weight = custom_label_0 = custom_label_1 = custom_label_2 = mileage_unit = ''

        dealership_name = 'Rohrman Toyota'
        list_url = response.meta.get('type_url')

        desc = ''.join(sel.xpath('//div[@class="dealer-comments__text truncate-comments"]//text()').extract()).replace('\n', '').replace('\r', '').strip()
        title = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-name').extract())
        Trim = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-trim').extract())
        condition = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-dotagging-item-condition').extract())
        vin = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-vin').extract())
        url = response.url
        msrp = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-dotagging-item-price').extract())
        price = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-price').extract())

        if msrp and price and int(msrp) != int(price) and msrp != '0' and price != '0':
            savings = '$' + str(int(float(msrp)) - int(float(price)))
        else:
            savings = ''

        if msrp != price:
            msrp = '$' + msrp
            price = '$' + price
        elif msrp == price:
            price = '' if price == '0' else '$' + price
            msrp = ''

        stock_number = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-stocknum').extract())
        make = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-make').extract())
        model = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-model').extract())
        brand = model
        year = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-year').extract())
        category = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-dotagging-item-category').extract())

        store_code = ''
        dealership_phone = ''
        dealer_type = 'Auto'
        dealership_address = ''
        dealer_url = 'https://www.rohrmantoyota.com'

        exterior_color = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-extcolor').extract())
        interior_color = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-intcolor').extract())
        engine = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-engine').extract())
        Fuel_Type = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-fueltype').extract())
        type_ = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-vehicletype').extract())
        body_style = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-bodystyle').extract()).strip()
        features = ' '.join(sel.xpath('//div[@id="vehicleFeaturesTabContent"]//text()').extract()).replace('\r', '').strip()
        features = ' '.join(features.split())
        location = ''.join(sel.xpath('//li[@class="adr"]//text()').extract())
        Transmission = ''.join(sel.xpath('//div[@class="vdp vdp--mod"]/@data-trans').extract())
        mileage_value = ''.join(sel.xpath('//li[@class="info__item info__item--mileage"]//span[@class="info__value"]/text()').extract())
        if mileage_value:
            mileage_unit = 'Miles'

        image_1 = 'https://www.rohrmantoyota.com' + ''.join(sel.xpath('//div[@class="thumbnails--desktop__top"]/a/@href').extract())
        image_2 = 'https://www.rohrmantoyota.com' + ''.join(sel.xpath('//a[@id="thumbnail--desktop--1"]/@href').extract())
        image_3 = 'https://www.rohrmantoyota.com' + ''.join(sel.xpath('//a[@id="thumbnail--desktop--2"]/@href').extract())
        Special_Tag = ''.join(sel.xpath('//div[@class="vehicle-status vehicle-status--plain"]//span[@class="vehicle-status__label"]/text()').extract())

        sk = hashlib.md5(vin.encode('utf8') + title.encode('utf8') + url.encode('utf8')).hexdigest()

        row = {
            "sk": sk,
            "dealership_name": dealership_name,
            "dealer_type": dealer_type,
            "dealership_address": dealership_address,
            "dealership_phone": dealership_phone,
            "store_code": store_code,
            "dealer_url": dealer_url,
            "cms": "",
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
            "sub_type": type_,
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

        # One row per (sk, creation_date): new snapshot each UTC day; same-day re-run updates
        supabase.table("scrap_rawdata").upsert(row, on_conflict="sk,creation_date").execute()
