import scrapy
import hashlib
from datetime import datetime, timezone
from scrapy.selector import Selector
from Rocmob.rocmob_cfg import supabase


class MoixrvhsSpider(scrapy.Spider):
    name = "moixrvhs"

    headers = {
        "User-Agent": "rogerbot",
        "Referer": "https://www.moixrv.com/"
    }

    inventory_urls = {
        "Inventory": "https://www.moixrv.com/rv-search?s=true&lots=1927&pagesize=12"
    }

    custom_settings = {
        "ENABLE_PROXY": False,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [429],
        'RETRY_DELAY': 10,
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def start_requests(self):
        for category, url in self.inventory_urls.items():
            yield scrapy.Request(
                url=url.format(1),
                callback=self.parse_inventory,
                headers=self.headers,
                meta={"category": category}
            )

    def parse_inventory(self, response):
        try:
            category = response.meta.get('category', '')
            next_page = ''.join(response.xpath(
                '//ul[@class="pagination"]//li//a[@class="next"]//@href').extract())
            nodes = response.xpath(
                '//ol[@class="unitList"]//li[contains(@class, "standard-template-v2")]')

            for node in nodes:
                url = node.xpath(
                    './/div[@class="h3 unit-title"]/a/@href').extract_first()
                title = node.xpath(
                    './/div[@class="h3 unit-title"]/a/text()').extract_first()
                stock_num = node.xpath(
                    './/div[@class="unit-stock-number-wrapper"]/span[@class="stock-number-text"]/text()').extract_first()
                price = node.xpath(
                    './/div[@class="sale-price-wrapper"]/span[@class="sale-price-text"]/text()').extract_first()
                msrp = node.xpath(
                    './/div[@class="reg-price-wrapper"]/span[@class="reg-price-text"]/text()').extract_first()
                savings = node.xpath(
                    './/div[@class="you-save-wrapper"]/span[@class="you-save-text"]/text()').extract_first()
                if url and 'https' not in url:
                    url = 'https://www.moixrv.com' + url
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_detail,
                        headers=self.headers,
                        meta={"title": title, "stock_num": stock_num,
                              "price": price, "msrp": msrp, "savings": savings}
                    )
            if next_page:
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse_inventory,
                    headers=self.headers,
                    meta={"category": category}
                )

        except Exception as e:
            self.logger.error("Failed to parse inventory: %s", e)

    def parse_detail(self, response):
        sel = Selector(response)
        finance_option = dealership_phone = doors = sleeps = dry_weight = length = trim = ''
        model = make = year = condition_ = type_ = sub_type = vin = brand = ''
        Special_Tag = Drivetrain = Fuel_Type = exterior_color = interior_color = ''
        seats = mileage_value = mileage_unit = engine = Transmission = body_style = ''
        Features = custom_label_0 = custom_label_1 = custom_label_2 = ''

        Special_Tag = ''.join(sel.xpath('//div[@class="sales-pitch alert alert-success"]//text()').extract()).strip()
        vin = ''.join(sel.xpath(
            '//table[@class="table specs-table"]//tbody//tr//td[@class="Specvin specs-desc"]//text()').extract()).strip()
        sleeps = ''.join(sel.xpath(
            '//table[@class="table specs-table"]//tbody//tr//td[@class="SpecSleeps specs-desc"]//text()').extract()).strip()
        length = ''.join(sel.xpath(
            '//table[@class="table specs-table"]//tbody//tr//td[@class="SpecLength specs-desc"]//text()').extract()).strip()
        dry_weight = ''.join(sel.xpath('//table[@class="table specs-table"]//tbody//tr//td[@class="SpecDryWeight specs-desc"]//text()').extract()).strip() or ''.join(sel.xpath('//table[@class="table specs-table"]//tbody//tr//td[@class="SpecGrossWeight specs-desc"]//text()').extract()).strip()

        price = ''.join(sel.xpath(
            '//ul[@class="price-info"]//li//span[@class="sale-price-text"]//text()').extract()).strip()
        msrp = ''.join(sel.xpath(
            '//ul[@class="price-info"]//li//span[@class="reg-price-text"]//text()').extract()).strip()
        savings = ''.join(sel.xpath(
            '//ul[@class="price-info"]//li//span[@class="you-save-text"]//text()').extract()).strip()

        title = ''.join(
            sel.xpath('//div[@class="container"]//div//h1//text()').extract()).strip()
        dealership_name = 'Moix RV Hot Springs Landing'
        dealer_type = 'RV'
        dealership_address = ''
        store_code = ''
        dealer_url = 'https://www.moixrv.com/'
        cms = 'Interact RV'

        condition_ = ''.join(sel.xpath(
            '//div[@class="container"]//div//h1//text()').extract()).strip().split()[0] if title else ''
        year = ''.join(sel.xpath(
            '//div[@class="container"]//div//h1//text()').extract()).strip().split()[1] if len(title.split()) > 1 else ''
        make = ''.join(sel.xpath("//@data-mfg").extract()).strip()
        model = ''.join(sel.xpath('//@data-brand').extract()).strip()
        brand = model.split()[0] if model else ''
        description = ''.join(sel.xpath(
            '//div[@class="description-wrapper"]//div[@class="UnitDescText-main"]//text()').extract()).strip().replace('\r', '').replace('\n', '')
        stock_number = ''.join(sel.xpath(
            '//div[@class="unit-stock-number-wrapper"]//span[@class="stock-number-text"]//text()').extract()).strip()
        url = response.url

        images = sel.xpath('//img//@llsrc').extract()
        image_1 = image_2 = image_3 = ''
        if len(images) >= 3:
            image_1, image_2, image_3 = images[0], images[1], images[2]
        elif len(images) == 2:
            image_1, image_2 = images[0], images[1]
        elif len(images) == 1:
            image_1 = images[0]

        type_ = ''.join(sel.xpath(
            '//div[@class="unit-rv-type-wrapper"]//a//span//text()').extract()).strip()
        location = ''.join(sel.xpath(
            '//div[@class="unit-location-wrapper"]//span[@class="unit-location-text"]//text()').extract()).strip()

        if model:
            trim = title.split(model)[-1].strip()
        else:
            trim = title.split(' ')[-1] if title else ''
        if brand == '':
            brand = model
        elif model == '':
            model = brand
        if model == '':
            model = make
        if vin == '':
            vin = stock_number

        custom_label_0 = ''.join(sel.xpath('//img[contains(@class, "tag-sold")]/@alt').extract()).strip() or ''.join(sel.xpath('//span[contains(@class, "tag-sale-pending")]/following-sibling::img[contains(@class, "tag-sale-pending")]/@alt').extract()).strip()

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
            "finance_option": finance_option,
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
            "features": Features,
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
