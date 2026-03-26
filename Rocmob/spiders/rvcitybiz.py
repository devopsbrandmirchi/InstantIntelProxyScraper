import scrapy
import hashlib
from datetime import datetime, timezone
from scrapy.selector import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


class RvcitybizSpider(scrapy.Spider):
    name = "rvcitybiz"
    start_urls = ['https://www.rvcity.biz']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        sel = Selector(response)
        vehicle_links = sel.xpath('//div[@class="inventory-unit"]//a[@class="listPages__imageLink"]/@href').extract()
        coming_soon_links = sel.xpath('//div[contains(@class, "inventory-unit")]//a[contains(@class, "unit-overlay") and contains(@class, "ov-comingsoon")]/@href').extract()
        sale_pending_links = sel.xpath('//div[contains(@class, "inventory-unit")]//a[contains(@class, "unit-overlay") and contains(@class, "ov-pending")]/@href').extract()
        other_links = sel.xpath('//div[contains(@class, "inventory-unit")]//a[contains(@class, "unit-overlay") and contains(@class, "listPages__imageLink")]/@href').extract()

        all_links = list(set(vehicle_links + coming_soon_links + sale_pending_links + other_links))
        for i in all_links:
            if 'http' not in i:
                url = response.urljoin(i)
                yield Request(url, callback=self.parse_next)

        for link in range(0, 45):
            url = 'https://www.rvcity.biz/search-results?curr_page={}'.format(link)
            yield Request(url, callback=self.parse)

    def parse_next(self, response):
        sel = Selector(response)
        url = response.url.strip()

        dealership_name = 'RV City'
        dealership_phone = ''
        dealer_type = 'RV'
        engine = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Engine Model:")]/following-sibling::p//text()').extract())
        dealership_address = ''
        cms = 'NetSource Media'
        dealer_url = 'https://www.rvcity.biz/'
        store_code = ''

        Finance_option = Special_Tag = sub_type = savings = ''
        Doors = Drivetrain = dry_weight = seats = Transmission = body_style = ''
        custom_label_0 = custom_label_1 = custom_label_2 = ''
        mileage_value = mileage_unit = ''

        title = ''.join(sel.xpath('//h1//text()').extract())
        condition_ = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Condition:")]/following-sibling::p//text()').extract())
        year = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Year:")]/following-sibling::p//text()').extract())
        length = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Length:")]/following-sibling::p//text()').extract())
        brand = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Model:")]/following-sibling::p//text()').extract())
        model = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Model:")]/following-sibling::p//text()').extract())
        make = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Brand:")]/following-sibling::p//text()').extract())
        vin = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "VIN:")]/following-sibling::p//text()').extract())
        if not vin:
            vin = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Stock #")]/following-sibling::p//text()').extract())
        stock_number = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Stock #")]/following-sibling::p//text()').extract())
        type_ = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Type:")]/following-sibling::p/a/text()').extract())
        sleeps = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Sleep Capacity:")]/following-sibling::p//text()').extract())
        exterior_color = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Exterior Color:")]/following-sibling::p//text()').extract())
        interior_color = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Interior Color:")]/following-sibling::p//text()').extract())
        location = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Location:")]/following-sibling::p//text()').extract())
        msrp = ''.join(sel.xpath('//div[@class="d-flex justify-content-between unit_msrp"]//text()[contains(., "MSRP")]/following::text()[2]').extract()).strip()
        price = ''.join(sel.xpath('//div[@class="d-flex justify-content-between unit_sale_price"]//text()[contains(., "Sale Price")]/following::text()[2]').extract()).strip()
        if not price:
            price = ''.join(sel.xpath('//div[@class="d-flex justify-content-between unit_price"]//text()[contains(., "Price")]/following::text()[2]').extract()).strip()
        Fuel_Type = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Fuel Type:")]/following-sibling::p//text()').extract())

        if msrp and price:
            try:
                msrp_ = msrp.strip('$').replace(',', '')
                price_ = price.strip('$').replace(',', '')
                savings = '$' + str(float(msrp_) - float(price_))
            except (ValueError, TypeError):
                pass

        thumbnail_path = response.xpath('//div[contains(@class, "detail__imageGrid__main")]//img[@rel="preload"]/@src').extract_first()
        image_1 = 'https:' + thumbnail_path if thumbnail_path else ''
        image_paths = response.xpath('//img[contains(@data-src, "/s3/img.rv/")]//@data-src').extract()[:3]
        image_2 = 'https:' + image_paths[1] if len(image_paths) > 1 else ''
        image_3 = 'https:' + image_paths[2] if len(image_paths) > 2 else ''

        description = ''.join(sel.xpath('//div[@class="detailPage__description"]//text()').extract()).strip()
        if not description:
            description = ''.join(sel.xpath('//div[@class="markdown prose w-full break-words dark:prose-invert dark"]//text()').extract()).replace('\t', '').replace('\r\n', '').strip()
        Features = ''.join(sel.xpath('//li[@class="list-group-item feat-header"]/b/text() | //li[@class="list-group-item"]/span[@class="ps-2"]/text()').extract())
        Trim = ''.join(sel.xpath('//div[@class="d-flex justify-content-between detailPage__specifications col"]//p[contains(text(), "Floorplan:")]/following-sibling::p//text()').extract())
        Special_Tag = ''.join(sel.xpath('//div[@class="d-flex flex-wrap align-items-center gap-2"]/p//text()').extract())

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
        except Exception as e:
            self.logger.error("Supabase error for %s: %s", url, e)
