import scrapy
import re
import hashlib
import json
from datetime import datetime, timezone
from scrapy import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


def _str(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return ' '.join(str(x) for x in value).strip()
    return str(value).strip()


class McdavidfordSpider(scrapy.Spider):
    name = "mcdavid"
    start_urls = ['https://www.mcdavidford.com/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory?start=0']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        data = json.loads(response.text)
        pagestart = data['pageInfo']['pageStart']
        totalcount = data['pageInfo']['totalCount']
        nodes = data['pageInfo']['trackingData']
        for i in nodes:
            location = i['address']['accountName']
            url = 'https://www.mcdavidford.com' + i['link']
            vin = i['vin']
            year = i['year']
            trim = i.get('trim', '')
            stocknumber = i['stockNumber']
            bodyStyle = i['bodyStyle']
            make = i['make']
            model = i['model']

            try:
                msrp = i['pricing']['msrp']
            except (KeyError, TypeError):
                msrp = ''
            condition_ = i['newOrUsed']
            try:
                price = i['pricing']['finalPrice']
            except (KeyError, TypeError):
                price = ''
            try:
                savings = i['pricing']['ABCRule']
            except (KeyError, TypeError):
                savings = ''
            transmission = i.get('transmission', '')
            ext_color = i.get('exteriorColor', '')
            fuel_type = i.get('fuelType', '')
            engine = i.get('engine', '')
            drivetrain = i.get('driveLine', '')
            doors = i.get('doors', '')
            int_color = i.get('interiorColor', '')
            milege_value = i.get('cityFuelEfficiency', '') or i.get('highwayFuelEfficiency', '')
            mileage_unit = 'MPG' if milege_value else ''
            images = i.get('images', []) or []
            image_1 = image_2 = image_3 = ''
            if len(images) >= 3:
                image_1 = images[0].get('uri', '') or ''
                image_2 = images[1].get('uri', '') or ''
                image_3 = images[2].get('uri', '') or ''
            elif len(images) == 2:
                image_1 = images[0].get('uri', '') or ''
                image_2 = images[1].get('uri', '') or ''
            elif len(images) == 1:
                image_1 = images[0].get('uri', '') or ''

            yield Request(
                url,
                callback=self.parse_next,
                meta={
                    'vin': vin, 'year': year, 'trim': trim, 'stocknumber': stocknumber,
                    'bodyStyle': bodyStyle, 'make': make, 'model': model,
                    'msrp': msrp, 'condition_': condition_, 'price': price, 'savings': savings,
                    'transmission': transmission, 'ext_color': ext_color, 'fuel_type': fuel_type,
                    'engine': engine, 'drivetrain': drivetrain, 'doors': doors,
                    'int_color': int_color, 'milege_value': milege_value, 'mileage_unit': mileage_unit,
                    'image_1': image_1, 'image_2': image_2, 'image_3': image_3,
                    'location': location,
                }
            )
        if totalcount != 0:
            page_no = int(pagestart) + 18
            next_url = 'https://www.mcdavidford.com/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory?start={}'.format(page_no)
            yield Request(next_url, callback=self.parse)

    def parse_next(self, response):
        sel = Selector(response)
        url = response.url
        vin = response.meta.get('vin', '')
        year = response.meta.get('year', '')
        trim = response.meta.get('trim', '')
        stock_number = response.meta.get('stocknumber', '')
        make = response.meta.get('make', '')

        model = ''
        if 'Mercedes-Benz' in url:
            match = re.search(r'Mercedes-Benz-(.*?)(?:-in-|/|$)', url)
            if match:
                model = match.group(1)
        else:
            match = re.search(r'\d{4}-[^-]+-(.*?)-in-', url)
            if match:
                model = match.group(1)
        brand = model

        msrp = response.meta.get('msrp', '')
        condn_ = sel.xpath("//h1[@class='vehicle-title m-0 line-height-reset']/span[1]/text()").extract()
        if condn_:
            condition_ = condn_[0].split()[0]
        else:
            condition_ = response.meta.get('condition_', '')
        price = response.meta.get('price', '')
        savings = ''.join(sel.xpath('//dd[@class="discount text-success"]//text()').extract()).replace('-', '').strip()
        if not savings and (msrp or price):
            savings = ''

        transmission = ''.join(sel.xpath('//li[@class="spec-item"]//span[contains(text(),"Transmission: ")]//following-sibling::span//text()').extract()) or ''.join(sel.xpath('//span[@class="package-title"][contains(text(),"Transmission:")]//text()').extract()).replace('Transmission: ', '')
        if not transmission:
            try:
                transmission = sel.xpath('//dt[contains(text(),"Transmission")]//following-sibling::dd//span//text()').extract()[0]
            except (IndexError, TypeError):
                transmission = response.meta.get('transmission', '')

        ext_color = response.meta.get('ext_color', '')
        fuel_type = response.meta.get('fuel_type', '')
        engine = ''.join(sel.xpath('//li[@class="spec-item"]//span[contains(text(),"Engine: ")]//following-sibling::span//text()').extract()) or ''.join(sel.xpath('//span[@class="package-title"][contains(text(),"Engine")]//text()').extract()).replace('Engine: ', '')
        if not engine:
            try:
                engine = sel.xpath('//dt[contains(text(),"Engine")]//following-sibling::dd//span//text()').extract()[0]
            except (IndexError, TypeError):
                engine = response.meta.get('engine', '')

        drivetrain = response.meta.get('drivetrain', '')
        doors = response.meta.get('doors', '')
        int_color = response.meta.get('int_color', '')
        mileage_value = response.meta.get('milege_value', '')
        mileage_unit = response.meta.get('mileage_unit', '')
        image_1 = response.meta.get('image_1', '')
        image_2 = response.meta.get('image_2', '')
        image_3 = response.meta.get('image_3', '')

        Finance_option = Special_Tag = sub_type = description = length = sleeps = ''
        custom_label_0 = custom_label_1 = custom_label_2 = ''

        try:
            dry_weight = ''.join(sel.xpath('//span[contains(text(),"Curb weight: ")]//following-sibling::span//text()').extract()).split('(')[-1].strip(')')
        except (IndexError, TypeError):
            dry_weight = ''
        seats = ''.join(sel.xpath('//span[contains(text(),"Max seating capacity: ")]//following-sibling::span//text()').extract())
        title = ''.join(sel.xpath('//h1//text()').extract())

        dealership_name = 'David McDavid Ford'
        dealer_type = 'Auto'
        dealership_address = '300 West Loop 820 S Fort Worth, TX 76108'
        dealership_phone = ''
        store_code = ''
        dealer_url = 'https://www.mcdavidford.com/'
        cms = ''
        features = ' '.join(sel.xpath('//div[@data-spec-category="standard features"]//text()').extract()).strip()

        bodystyle = response.meta.get('bodyStyle', '') or ''
        words = bodystyle.split(" ", 1)
        type_ = words[0] if words else ''
        sub_type = words[1] if len(words) > 1 else ''
        body_style = type_

        location = ''.join(sel.xpath('//li[contains(@class, "liUnit LiInvLocation")]//label[contains(text(), "Location")]/following-sibling::span[@class="spnUnitValue"]/text()').extract()).strip()
        if not location:
            location = response.meta.get('location', '')

        try:
            sk = hashlib.md5((_str(vin) + _str(title) + url).encode('utf8')).hexdigest()
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
            "year_": _str(year),
            "make": _str(make),
            "model": _str(model),
            "brand": _str(brand),
            "vin": _str(vin),
            "stock_number": _str(stock_number),
            "url": url,
            "msrp": _str(msrp),
            "price": _str(price),
            "savings": _str(savings),
            "finance_option": Finance_option,
            "special_tag": Special_Tag,
            "type_": type_,
            "sub_type": sub_type,
            "location": location,
            "image_url": _str(image_1),
            "image_url_2": _str(image_2),
            "image_url_3": _str(image_3),
            "title": title,
            "description": description,
            "trim": _str(trim),
            "length": length,
            "doors": _str(doors),
            "drivetrain": _str(drivetrain),
            "fuel_type": _str(fuel_type),
            "exterior_color": _str(ext_color),
            "interior_color": _str(int_color),
            "sleeps": sleeps,
            "seats": _str(seats),
            "dry_weight": _str(dry_weight),
            "mileage_value": _str(mileage_value),
            "mileage_unit": mileage_unit,
            "engine": _str(engine),
            "transmission": _str(transmission),
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
