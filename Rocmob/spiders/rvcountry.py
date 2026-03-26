import scrapy
import hashlib
import json
from datetime import datetime, timezone
from scrapy import Selector
from scrapy import Request
import requests
from scrapy.exceptions import CloseSpider
from Rocmob.rocmob_cfg import supabase


class RvcountrySpider(scrapy.Spider):
    name = "rvcountry"
    request_counter = 0
    previous_request_url = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()

    def start_requests(self):
        cookies = {
            'PHPSESSID': '05at9n5p81fmrilv02aci7g0dt',
            '_fbp': 'fb.1.1730195487514.154547786295558451',
            'gg_ignore_queue': '1',
            'cookieyes-consent': 'consentid:Z1AwUnpwSTU2TWhPOEZzU1JFcVpacTQ1M09YREtoSmc,consent:yes,action:yes,necessary:yes,functional:yes,analytics:yes,performance:yes,advertisement:yes,other:yes',
            '__ggtruid': '1730198175405.be35087e-644d-004c-aec8-ed0feea31690',
        }
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://rvcountry.com',
            'Referer': 'https://rvcountry.com/rvs-for-sale/?lot=Fresno_Ca',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }

        classs = ['Car', 'Class A', 'Class B', 'Class C', 'Fifth Wheel', 'Fold Down', 'Pickup Truck', 'Toy Hauler', 'Travel Trailer', 'Truck Camper']

        for class_type in classs:
            data = {
                'action': 'dtk_im2_ajax_srp_getPosts',
                'selectedOptions[marketclass][value]': '{}'.format(class_type),
                'selectedOptions[lot][value]': 'Fresno Ca',
                'page': '1',
                'limit': '15',
                'sort': '0',
                'latlong[latitude]': '',
                'latlong[longitude]': '',
            }

            try:
                response = requests.post('https://rvcountry.com/wp-admin/admin-ajax.php', cookies=cookies, headers=headers, data=data)
                total_pages = json.loads(response.text).get('pagesMax', 0)

                for k in range(0, int(total_pages) + 2):
                    url = 'https://rvcountry.com/rvs-for-sale&pagination={}'.format(k)

                    if self.previous_request_url == url:
                        self.request_counter += 1
                    else:
                        self.previous_request_url = url
                        self.request_counter = 1

                    if self.request_counter > 3:
                        self.logger.warning("Request repeated %s times. Stopping the spider.", self.request_counter)
                        raise CloseSpider("Repeated requests detected, stopping spider.")

                    headers = dict(headers)
                    headers['Referer'] = url

                    post_data = {
                        'action': 'dtk_im2_ajax_srp_getPosts',
                        'selectedOptions[marketclass][value]': '{}'.format(class_type),
                        'selectedOptions[lot][value]': 'Fresno Ca',
                        'page': str(k),
                        'limit': '15',
                        'sort': '0',
                        'latlong[latitude]': '',
                        'latlong[longitude]': '',
                    }

                    response = requests.post('https://rvcountry.com/wp-admin/admin-ajax.php', cookies=cookies, headers=headers, data=post_data)
                    posts = json.loads(response.text).get('posts', [])
                    for i in posts:
                        item_url = i.get('url', '')
                        description = i.get('description', '')
                        images = i.get('images', [])
                        title = i.get('title', '')
                        yield Request(item_url, callback=self.parse, meta={'description': description, 'images': images, 'title': title})

            except Exception as e:
                self.logger.error("Error in request: %s", e)
                raise CloseSpider("Error occurred during scraping")

    def parse(self, response):
        sel = Selector(response)
        url = response.url
        dealership_name = 'RV Country Fresno'
        finance_option = dealership_phone = doors = sleeps = dry_weight = length = trim = ''
        model = make = year = condition_ = type_ = sub_type = vin = brand = ''
        Special_Tag = Drivetrain = Fuel_Type = exterior_color = interior_color = ''
        seats = mileage_value = mileage_unit = engine = Transmission = body_style = ''
        Features = custom_label_0 = custom_label_1 = custom_label_2 = ''

        dealer_type = 'RV'
        dealership_address = ''
        store_code = ''
        dealer_url = 'https://www.rvcountry.com/'
        cms = 'Stealth AI Suite'

        images = response.meta.get('images', []) or []
        image_1 = image_2 = image_3 = ''
        if len(images) >= 3:
            image_1, image_2, image_3 = images[0], images[1], images[2]
        elif len(images) == 2:
            image_1, image_2 = images[0], images[1]
        elif len(images) == 1:
            image_1 = images[0]

        titles = response.meta.get('title', '')
        title = titles.replace('<br>', '  ').replace('<span>', '  ').replace('</span>', ' ') if titles else ''

        pricing_text = ''.join(sel.xpath('//div[@class="pricing"]//span//text()').extract())
        if 'PAYMENTS AS LOW AS:' in pricing_text:
            finance_option = 'PAYMENTS AS LOW AS:' + pricing_text.split('PAYMENTS AS LOW AS:')[-1]

        msrp = ''.join(sel.xpath('//span[@class="price msrp"]//span//text()').extract())
        savings = ''.join(sel.xpath('//span[@class="price savings"]//span//text()').extract())
        price = ''.join(sel.xpath('//span[@class="price salesprice"]//span//text()').extract())
        location = ''.join(sel.xpath('//span[@class="location name"]//text()').extract())
        stock_number = ''.join(sel.xpath("//div/div[@class='specification'][1]/div[@class='right']/span/text()").extract()).strip()
        vin = ''.join(sel.xpath("//div/div[@class='specification'][2]/div[@class='right']/span/text()").extract()).strip()
        condition_ = ''.join(sel.xpath("//div/div[@class='specification'][3]/div[@class='right']/span/text()").extract()).strip()
        year = ''.join(sel.xpath("//div/div[@class='specification'][4]/div[@class='right']/span/text()").extract()).strip()
        make = ''.join(sel.xpath("//div/div[@class='specification'][5]/div[@class='right']/span/text()").extract()).strip()
        model = ''.join(sel.xpath("//div/div[@class='specification'][6]/div[@class='right']/span/text()").extract()).strip()
        brand = model
        trim = ''.join(sel.xpath("//div/div[@class='specification'][7]/div[@class='right']/span/text()").extract()).strip()
        location = ''.join(sel.xpath("//span[@class='city_state']/text()").extract()).strip()

        description = ''

        types = [
            "TRAVEL TRAILER", "FIFTH WHEEL", "CLASS A DIESEL MOTORHOME", "TRAVEL TRAILER HAULER",
            "CLASS A MOTORHOME", "FIFTH WHEEL HAULER", "CLASS C MOTORHOME", "CLASS C DIESEL",
            "DESTINATION TRAILER", "CLASS B MOTORHOME", "CLASS B DIESEL", "FOLD DOWN"
        ]
        desc = sel.xpath("//div[@class='page selected']//text()").extract()
        type1_ = ''
        types_found = [t for t in types if any(t.lower() in (d or '').lower() for d in desc)]
        if types_found:
            type1_ = types_found[0]
        type_ = type1_

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
            self.logger.error("Error in parsing or saving data: %s", e)
