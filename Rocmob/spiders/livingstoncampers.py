import scrapy
import hashlib
import json
from datetime import datetime, timezone
from scrapy.selector import Selector
from scrapy.http import Request
from Rocmob.rocmob_cfg import supabase


class LivingstoncampersSpider(scrapy.Spider):
    name = "Livingston"

    name = "Livingston"
    custom_settings = {
        "ENABLE_PROXY": False,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [429, 500, 502, 503, 504],
    }
    start_urls = ['https://www.livingstoncampersales.com/rebraco/unitlist/results?s=true&criteria=%7B%22HideLibrary%22%3Atrue%2C%22OnlyLibrary%22%3Afalse%2C%22UnitAgeFilter%22%3A0%2C%22InvertTagFilter%22%3Afalse%2C%22InvertTypeFilter%22%3Afalse%2C%22StatusId%22%3A%222%22%2C%22InvertManufacturerFilter%22%3Afalse%2C%22PriceFilters%22%3A%5B%5D%2C%22MonthlyPaymentsFilters%22%3A%5B%5D%2C%22PropVals%22%3A%7B%7D%2C%22ResultsSortString%22%3A%22condition-desc%2Cprice-asc%22%2C%22PageSize%22%3A24%2C%22PageNum%22%3A0%2C%22NoResultsPredetermined%22%3Afalse%2C%22IsCompact%22%3Afalse%7D&config=%7B%22PageId%22%3A440002%2C%22GlpForm%22%3A%221182%22%2C%22GlpForceForm%22%3A%221182%22%2C%22GlpNoPriceConfirm%22%3A1435%2C%22GlpPriceConfirm%22%3A1436%2C%22Slider%22%3Afalse%2C%22SliderPaused%22%3Afalse%2C%22VertSlider%22%3Afalse%2C%22VisibleSlides%22%3A3%2C%22IsCompact%22%3Afalse%2C%22Limit%22%3A0%2C%22SearchMode%22%3Afalse%2C%22DefaultSortMode%22%3A%22condition-desc%2Cprice-asc%22%2C%22UseFqdnUnitLinks%22%3Afalse%2C%22NumberOfSoldIfNoActive%22%3A0%2C%22NoResultsSnippetId%22%3A0%2C%22ShowSimilarUnitsIfNoResults%22%3Afalse%2C%22DefaultPageSize%22%3A24%2C%22ImageWidth%22%3A400%2C%22ImageHeight%22%3A0%2C%22NoPriceText%22%3A%22Call%20for%20price!%22%2C%22ShowPaymentsAround%22%3Atrue%2C%22ShowPaymentsAroundInCompactMode%22%3Afalse%2C%22DefaultToGridMode%22%3Afalse%2C%22DisableAjax%22%3Afalse%2C%22PriceTooltip%22%3A%22%22%2C%22FavoritesMode%22%3Afalse%2C%22ConsolidatedMode%22%3Afalse%7D']
    
    def __init__(self, *args, **kwargs):
        super(LivingstoncampersSpider, self).__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
    def parse (self,response):
        json_data = json.loads(response.text)
        units = json_data['Units']
        for i in units:
            try:
                all_ids = i['ConsolidatedUnitIds'].split(',')
            except:
                all_ids = [i['UnitId']]
            for UnitId in all_ids:
                url = 'https://www.livingstoncampersales.com/product/new-2025-forest-river-rv-surveyor-legend-x-27camp-{}-29'.format(UnitId)
                yield Request(url, callback=self.parse_next, meta={'list_url':'https://www.livingstoncampersales.com/rv-search', 'UnitId':UnitId}, dont_filter=True)
        # next_page = int((response.url).split('&page=')[-1])
        try:
            next_page = int((response.url).split('&page=')[-1])
        except:
            next_page = 1
        total_units = json_data['TotalUnits']
        HasExactResults = json_data['HasExactResults']
        if HasExactResults == True and total_units !=0:
            next_page += 1
            next_url = 'https://www.livingstoncampersales.com/rebraco/unitlist/results?s=true&criteria=%7B%22HideLibrary%22%3Atrue%2C%22OnlyLibrary%22%3Afalse%2C%22UnitAgeFilter%22%3A0%2C%22InvertTagFilter%22%3Afalse%2C%22InvertTypeFilter%22%3Afalse%2C%22StatusId%22%3A%222%22%2C%22InvertManufacturerFilter%22%3Afalse%2C%22PriceFilters%22%3A%5B%5D%2C%22MonthlyPaymentsFilters%22%3A%5B%5D%2C%22PropVals%22%3A%7B%7D%2C%22ResultsSortString%22%3A%22condition-desc%2Cprice-asc%22%2C%22PageSize%22%3A24%2C%22PageNum%22%3A0%2C%22NoResultsPredetermined%22%3Afalse%2C%22IsCompact%22%3Afalse%7D&config=%7B%22PageId%22%3A440002%2C%22GlpForm%22%3A%221182%22%2C%22GlpForceForm%22%3A%221182%22%2C%22GlpNoPriceConfirm%22%3A1435%2C%22GlpPriceConfirm%22%3A1436%2C%22Slider%22%3Afalse%2C%22SliderPaused%22%3Afalse%2C%22VertSlider%22%3Afalse%2C%22VisibleSlides%22%3A3%2C%22IsCompact%22%3Afalse%2C%22Limit%22%3A0%2C%22SearchMode%22%3Afalse%2C%22DefaultSortMode%22%3A%22condition-desc%2Cprice-asc%22%2C%22UseFqdnUnitLinks%22%3Afalse%2C%22NumberOfSoldIfNoActive%22%3A0%2C%22NoResultsSnippetId%22%3A0%2C%22ShowSimilarUnitsIfNoResults%22%3Afalse%2C%22DefaultPageSize%22%3A24%2C%22ImageWidth%22%3A400%2C%22ImageHeight%22%3A0%2C%22NoPriceText%22%3A%22Call%20for%20price!%22%2C%22ShowPaymentsAround%22%3Atrue%2C%22ShowPaymentsAroundInCompactMode%22%3Afalse%2C%22DefaultToGridMode%22%3Afalse%2C%22DisableAjax%22%3Afalse%2C%22PriceTooltip%22%3A%22%22%2C%22FavoritesMode%22%3Afalse%2C%22ConsolidatedMode%22%3Afalse%7D&page={}'.format(next_page)
            print(next_url)
            yield Request(next_url, callback=self.parse, meta={'list_url':response.url})
    def parse_next(self, response):
            sel = Selector(response)
            UnitId = response.meta.get('UnitId')
            store_code = ''
            dealership_name = "Livingston Campers"
            dealership_phone = ''
            dealer_type = 'RV'
            dealership_address = ""
            dealer_url = 'https://www.livingstoncampersales.com'
            cms = 'Interact RV'
            Finance_option, Special_Tag, Trim, Doors, Drivetrain, Fuel_Type, exterior_color, interior_color, seats, mileage_value, mileage_unit, sleeps, Transmission, body_style, custom_label_0, custom_label_1, custom_label_2, sub_type = ['']*18
            Features = ' '.join(sel.xpath('//div[@class="features-wrapper"]//text()').extract()).replace('\n', '').replace('\r', '').replace('See All Features','').strip().replace('\t', '').replace('                                             ','')
            main_url = response.meta.get('list_url')
            title  = ''.join(sel.xpath('//h1/text()').extract()).replace('\n', '').strip()
            url_title = title.lower().replace(' ','-')
            title_link = ''.join(sel.xpath('//@data-unitlink').extract())
            url = 'https://www.livingstoncampersales.com' + title_link
            year = ''.join(sel.xpath('//div/@data-year').extract()).replace('\n', '').strip()
            condition = title.split(year)[0]
            desc = ' '.join(sel.xpath('//div[@class="description-wrapper"]//text()').extract()).replace('\n', '').replace('\r', '').replace('Read More', '').strip()
            vin = ''.join(sel.xpath('//td[contains(text(), "VIN")]/following-sibling::td/text()').extract()).replace('\n', '').strip()
            length = ''.join(sel.xpath('//svg[@class="fa fa-length"]//following-sibling::div[@class="overview-tile-title"]/text()').extract()).replace('Long','').strip()
            dry_weight = ''.join(sel.xpath('//td[@class="SpecDryWeight specs-desc"]/text()').extract()).replace('\n', '').strip()
            if not dry_weight:
                dry_weight = ''.join(sel.xpath('//td[@class="SpecGrossWeight specs-desc"]/text()').extract()).replace('\n', '').strip()
            sleeps = ''.join(sel.xpath('//td[@class="SpecSleeps specs-desc"]/text()').extract()).replace('\n', '').strip()
            msrp = ''.join(sel.xpath('//div/@data-msrp').extract()).replace('\n', '').strip()
            print(f"Msrp : {msrp}")
            if not msrp:
                msrp = ''.join(sel.xpath('//span[contains(text(), "List Price: ")]/following-sibling::span/text()').extract()).replace('\n', '').strip()
            price = ''.join(sel.xpath('//div/@data-saleprice').extract()).replace('\n', '').strip()
            print(f"Price : {price}")
            savings = ''.join(sel.xpath('//span[@class="you-save-text"]/text()').extract()).replace('\n', '').strip()
            Finance_option = ''.join(sel.xpath('//div[@class="payments-around-container"]//span//text()').extract()).replace('\n', '').strip()
            stock_number = ''.join(sel.xpath('//span[@class="stock-number-text"]/text()').extract()).replace('\n', '').strip()
            if not vin:
                vin = stock_number
            type_ = ''.join(sel.xpath('//span[@class="rv-type-label"]/text()').extract()).replace('\n', '').strip()
            location = ''.join(sel.xpath('//span[@class="unit-location-text"]/text()').extract()).replace('\n', '').strip()
            number = url.split('-')[-2]
            Special_Tag = ''.join(sel.xpath('//div[@class="sales-pitch alert alert-success"]/text()').extract()).replace('\n', '').strip()
            Trim ,Doors, Drivetrain = ['']*3
            seats, mileage_value , mileage_unit, Transmission, body_style , custom_label_0 , custom_label_1, custom_label_2 = ['']*8
            exterior_color = ''.join(sel.xpath('//td[@class="SpecExteriorColor specs-desc"]/text()').extract()).replace('\n', '').strip()
            interior_color = ''.join(sel.xpath('//td[@class="SpecInteriorColor specs-desc"]/text()').extract()).replace('\n', '').strip()
            engine = ''.join(sel.xpath('//td[@class="SpecEngine specs-desc"]/text()').extract()).replace('\n', '').strip()
            Fuel_Type = ''.join(sel.xpath('//td[@class="SpecFuelType specs-desc"]/text()').extract()).replace('\n', '').strip()
            Trim = ''.join(sel.xpath('//div/@data-unitname').extract()).replace('\n', '').strip()
            custom_label_0 = ''.join(sel.xpath('//img[contains(@class, "tag-sold")]/@alt').extract()).strip() or ''.join(sel.xpath('//span[contains(@class, "tag-sale-pending")]/following-sibling::img[contains(@class, "tag-sale-pending")]/@alt').extract()).strip()
            brand = ''.join(sel.xpath('//div/@data-brand').extract()).replace('\n', '').strip()
            model = ''.join(sel.xpath('//div/@data-brand').extract()).replace('\n', '').strip()
            make = ''.join(sel.xpath('//div/@data-mfg').extract()).replace('\n', '').strip()
            if model =='':
                model=title.split(year)[-1].split(Trim)[0].strip().split(' ')[-1]
            if make =='':
                make = ' '.join(title.split(year)[-1].split(Trim)[0].strip().split(' ')[:-1])
            if brand=='Unknown':
                brand=''
            if model=='Unknown':
                model=title.split(year)[-1].split(Trim)[0].strip().split(' ')[-1]
            if brand=='':
                brand = model
            images = sel.xpath('//img/@llsrc').extract()
            image_1, image_2, image_3 = ['']*3
            if len(images)>1 and images:
                try:
                    image_1 = images[0]
                    image_2 = images[1]
                    image_3 = images[2]
                except:
                    image_2 = ''
            sk = hashlib.md5(vin.encode('utf8') + title.encode('utf8') +
                                                        response.url.encode('utf8')).hexdigest()
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

