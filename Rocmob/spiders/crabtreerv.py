import scrapy
import re
import hashlib
import json
from datetime import datetime, timezone
from scrapy.selector import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


class CrabtreervSpider(scrapy.Spider):
    name = "crabtreerv"

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [429, 500, 502, 503, 504],
    }

    start_urls = ['https://www.crabtreerv.com/rebraco/unitlist/results?s=true&criteria=%7B%22HideLibrary%22%3A%20true%2C%20%22OnlyLibrary%22%3A%20false%2C%20%22UnitAgeFilter%22%3A%200%2C%20%22InvertTagFilter%22%3A%20false%2C%20%22InvertTypeFilter%22%3A%20false%2C%20%22StatusId%22%3A%20%222%22%2C%20%22PriceFilters%22%3A%20%5B%5D%2C%20%22MonthlyPaymentsFilters%22%3A%20%5B%5D%2C%20%22PropVals%22%3A%20%7B%7D%2C%20%22PageSize%22%3A%2024%2C%20%22PageNum%22%3A%200%2C%20%22IsCompact%22%3A%20false%7D&config=%7B%22PageId%22%3A%2045720%2C%20%22GlpForm%22%3A%20%22%7B%5Cn%20%20%5C%22formSnippetId%5C%22%3A%20171543%2C%5Cn%20%20%5C%22settings%5C%22%3A%20%5B%5D%5Cn%7D%22%2C%20%22GlpForceForm%22%3A%20%22%7B%5Cn%20%20%5C%22formSnippetId%5C%22%3A%20247282%2C%5Cn%20%20%5C%22settings%5C%22%3A%20%5B%5D%5Cn%7D%22%2C%20%22GlpNoPriceConfirm%22%3A%201435%2C%20%22GlpPriceConfirm%22%3A%201436%2C%20%22Slider%22%3A%20false%2C%20%22SliderPaused%22%3A%20false%2C%20%22VertSlider%22%3A%20false%2C%20%22VisibleSlides%22%3A%203%2C%20%22IsCompact%22%3A%20false%2C%20%22Limit%22%3A%200%2C%20%22SearchMode%22%3A%20false%2C%20%22DefaultSortMode%22%3A%20%22%22%2C%20%22UseFqdnUnitLinks%22%3A%20false%2C%20%22NumberOfSoldIfNoActive%22%3A%200%2C%20%22NoResultsSnippetId%22%3A%200%2C%20%22ShowSimilarUnitsIfNoResults%22%3A%20false%2C%20%22DefaultPageSize%22%3A%2024%2C%20%22ImageWidth%22%3A%20800%2C%20%22ImageHeight%22%3A%20600%2C%20%22NoPriceText%22%3A%20%22Call%20for%20price%21%22%2C%20%22ShowPaymentsAround%22%3A%20true%2C%20%22ShowPaymentsAroundInCompactMode%22%3A%20false%2C%20%22DefaultToGridMode%22%3A%20false%2C%20%22DisableAjax%22%3A%20false%2C%20%22PriceTooltip%22%3A%20%22%22%2C%20%22FavoritesMode%22%3A%20false%2C%20%22ConsolidatedMode%22%3A%20false%7D']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def parse(self, response):
        json_data = json.loads(response.text)
        units = json_data.get('Units', [])
        for i in units:
            try:
                all_ids = i['ConsolidatedUnitIds'].split(',')
            except (KeyError, TypeError):
                all_ids = [i.get('UnitId', '')]
            for UnitId in all_ids:
                url = 'https://www.crabtreerv.com/product/new-2025-coachmen-rv-catalina-legacy-edition-243rbs-{}-29'.format(UnitId)
                yield Request(url, callback=self.parse_next, meta={'list_url': 'https://www.crabtreerv.com/rv-search?s=true', 'UnitId': UnitId}, dont_filter=True)
        try:
            next_page = int((response.url).split('&page=')[-1])
        except (ValueError, IndexError):
            next_page = 1
        total_units = json_data.get('TotalUnits', 0)
        HasExactResults = json_data.get('HasExactResults', False)
        if HasExactResults and total_units != 0:
            next_page += 1
            next_url = 'https://www.crabtreerv.com/rebraco/unitlist/results?s=true&criteria=%7B%22HideLibrary%22%3A%20true%2C%20%22OnlyLibrary%22%3A%20false%2C%20%22UnitAgeFilter%22%3A%200%2C%20%22InvertTagFilter%22%3A%20false%2C%20%22InvertTypeFilter%22%3A%20false%2C%20%22StatusId%22%3A%20%222%22%2C%20%22PriceFilters%22%3A%20%5B%5D%2C%20%22MonthlyPaymentsFilters%22%3A%20%5B%5D%2C%20%22PropVals%22%3A%20%7B%7D%2C%20%22PageSize%22%3A%2024%2C%20%22PageNum%22%3A%200%2C%20%22IsCompact%22%3A%20false%7D&config=%7B%22PageId%22%3A%2045720%2C%20%22GlpForm%22%3A%20%22%7B%5Cn%20%20%5C%22formSnippetId%5C%22%3A%20171543%2C%5Cn%20%20%5C%22settings%5C%22%3A%20%5B%5D%5Cn%7D%22%2C%20%22GlpForceForm%22%3A%20%22%7B%5Cn%20%20%5C%22formSnippetId%5C%22%3A%20247282%2C%5Cn%20%20%5C%22settings%5C%22%3A%20%5B%5D%5Cn%7D%22%2C%20%22GlpNoPriceConfirm%22%3A%201435%2C%20%22GlpPriceConfirm%22%3A%201436%2C%20%22Slider%22%3A%20false%2C%20%22SliderPaused%22%3A%20false%2C%20%22VertSlider%22%3A%20false%2C%20%22VisibleSlides%22%3A%203%2C%20%22IsCompact%22%3A%20false%2C%20%22Limit%22%3A%200%2C%20%22SearchMode%22%3A%20false%2C%20%22DefaultSortMode%22%3A%20%22%22%2C%20%22UseFqdnUnitLinks%22%3A%20false%2C%20%22NumberOfSoldIfNoActive%22%3A%200%2C%20%22NoResultsSnippetId%22%3A%200%2C%20%22ShowSimilarUnitsIfNoResults%22%3A%20false%2C%20%22DefaultPageSize%22%3A%2024%2C%20%22ImageWidth%22%3A%20800%2C%20%22ImageHeight%22%3A%20600%2C%20%22NoPriceText%22%3A%20%22Call%20for%20price%21%22%2C%20%22ShowPaymentsAround%22%3A%20true%2C%20%22ShowPaymentsAroundInCompactMode%22%3A%20false%2C%20%22DefaultToGridMode%22%3A%20false%2C%20%22DisableAjax%22%3A%20false%2C%20%22PriceTooltip%22%3A%20%22%22%2C%20%22FavoritesMode%22%3A%20false%2C%20%22ConsolidatedMode%22%3A%20false%7D&page={}'.format(next_page)
            yield Request(next_url, callback=self.parse, meta={'list_url': response.url})

    def parse_next(self, response):
        sel = Selector(response)
        store_code = ''
        dealership_name = 'Crabtree RV'
        dealership_phone = ''
        dealer_type = 'RV'
        dealership_address = "400 Heather Lane Alma, AR 72921"
        dealer_url = 'https://www.crabtreerv.com/'
        cms = 'Interact RV'

        Finance_option = Special_Tag = Trim = Doors = Drivetrain = Fuel_Type = ''
        exterior_color = interior_color = seats = mileage_value = mileage_unit = ''
        sleeps = Transmission = body_style = sub_type = ''
        custom_label_0 = custom_label_1 = custom_label_2 = ''

        Features = ' '.join(sel.xpath('//div[@class="features-wrapper"]//text()').extract()).replace('\n', '').replace('\r', '').replace('See All Features', '').strip().replace('\t', '').replace('                                             ', '')
        Features = ' '.join(Features.split())

        title = ''.join(sel.xpath('//h1/text()').extract()).replace('\n', '').strip()
        title_link = ''.join(sel.xpath('//@data-unitlink').extract())
        url = 'https://www.crabtreerv.com' + title_link if title_link else response.url
        year = ''.join(sel.xpath('//div/@data-year').extract()).replace('\n', '').strip()
        condition_ = title.split(year)[0].strip() if year else ''
        desc = ' '.join(sel.xpath('//div[@class="description-wrapper"]//text()').extract()).replace('\n', '').replace('\r', '').replace('Read More', '').strip()

        vin = ''.join(sel.xpath('//td[contains(text(), "VIN")]/following-sibling::td/text()').extract()).replace('\n', '').strip()
        length = ''.join(sel.xpath('//svg[@class="fa fa-length"]//following-sibling::div[@class="overview-tile-title"]/text()').extract()).replace('Long', '').strip()
        dry_weight = ''.join(sel.xpath('//td[@class="SpecDryWeight specs-desc"]/text()').extract()).replace('\n', '').strip()
        if not dry_weight:
            dry_weight = ''.join(sel.xpath('//td[@class="SpecGrossWeight specs-desc"]/text()').extract()).replace('\n', '').strip()
        sleeps = ''.join(sel.xpath('//td[@class="SpecSleeps specs-desc"]/text()').extract()).replace('\n', '').strip()
        msrp = ''.join(sel.xpath('//span[contains(text(), "Retail Price")]/following-sibling::div/text()[normalize-space()]').extract()).replace('\n', '').strip()
        if not msrp:
            msrp = ''.join(sel.xpath('//span[@class="PriceLabel" and contains(text(), "List Price:")]/following-sibling::span[@class="PriceText"]/text()').extract()).replace('\n', '').strip()
        price = ''.join(sel.xpath('//span[contains(text(), "Our Price")]/following-sibling::div/text()[normalize-space()]').extract()).strip()
        savings = ''.join(sel.xpath('//span[contains(text(), "Rebate")]/following-sibling::div/text()[normalize-space()]').extract()).strip()
        Finance_option = ''.join(sel.xpath('//div[@class="payments-around-container"]//span//text()').extract()).replace('\n', '').strip()
        stock_number = ''.join(sel.xpath('//div[@class="StockNo"]/text()').extract()).replace('\n', '').strip()
        stock_number = re.sub(r'\D', '', stock_number)
        if not vin:
            vin = stock_number
        type_ = ''.join(sel.xpath('//div//@data-type').extract())
        sub_type = type_
        location = ''.join(sel.xpath('//li[@class="liUnit LiInvlocation"]/span/text()').extract()).replace('\n', '').strip()
        Special_Tag = ''.join(sel.xpath('//span[@class="salesPitch"]/text()').extract()).replace('\n', '').strip()

        exterior_color = ''.join(sel.xpath('//td[@class="SpecExteriorColor specs-desc"]/text()').extract()).replace('\n', '').strip()
        interior_color = ''.join(sel.xpath('//td[@class="SpecInteriorColor specs-desc"]/text()').extract()).replace('\n', '').strip()
        engine = ''.join(sel.xpath('//td[@class="SpecEngine specs-desc"]/text()').extract()).replace('\n', '').strip()
        Fuel_Type = ''.join(sel.xpath('//td[@class="SpecFuelType specs-desc"]/text()').extract()).replace('\n', '').strip()
        Trim = ''.join(sel.xpath('//div/@data-unitname').extract()).replace('\n', '').strip()
        custom_label_0 = ''.join(sel.xpath('//img[contains(@class, "tag-sold")]/@alt').extract()).strip() or ''.join(sel.xpath('//span[contains(@class, "tag-sale-pending")]/following-sibling::img[contains(@class, "tag-sale-pending")]/@alt').extract()).strip()
        brand = ''.join(sel.xpath('//div/@data-brand').extract()).replace('\n', '').strip()
        model = ''.join(sel.xpath('//div/@data-brand').extract()).replace('\n', '').strip()
        make = ''.join(sel.xpath('//div/@data-mfg').extract()).replace('\n', '').strip()
        if model == '' and year and Trim:
            model = title.split(year)[-1].split(Trim)[0].strip().split(' ')[-1]
        if make == '' and year and Trim:
            make = ' '.join(title.split(year)[-1].split(Trim)[0].strip().split(' ')[:-1])
        if brand == 'Unknown':
            brand = ''
        if brand == '':
            brand = model

        images = sel.xpath('//img/@llsrc').extract()
        image_1 = image_2 = image_3 = ''
        if len(images) >= 3:
            image_1, image_2, image_3 = images[0], images[1], images[2]
        elif len(images) == 2:
            image_1, image_2 = images[0], images[1]
        elif len(images) == 1:
            image_1 = images[0]

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
