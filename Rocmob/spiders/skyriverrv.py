"""
Sky River RV spider (Scout RV Google feed):
  - vehicle data from the XML feed at /api/feeds/google (no pagination)
  - location per unit from /api/inventory (multi-lot dealer); units missing
    there fall back to the location block on the unit detail page
  - empty VIN falls back to stock number
  - curl_cffi gets past the Vercel security checkpoint on detail pages
  - upserts into Supabase scrap_rawdata
"""

import hashlib
import html
import json
import re
from datetime import datetime, timezone

import scrapy
from scrapy.selector import Selector

from Rocmob.rocmob_cfg import supabase

BASE_URL = 'https://www.skyriverrv.com'
FEED_URL = f'{BASE_URL}/api/feeds/google'
INVENTORY_API_URL = f'{BASE_URL}/api/inventory'

DETAIL_LOCATION_RE = re.compile(r'"location":\{"id":"[^"]+"(.*?)\}', re.S)


def format_location(city, state):
    city = (city or '').strip()
    state = (state or '').strip()
    return ', '.join(part for part in (city, state) if part)


def format_address(street, city, state, zip_code):
    city_state = format_location(city, state)
    line = ', '.join(part for part in ((street or '').strip(), city_state) if part)
    return f"{line} {(zip_code or '').strip()}".strip()


def clean_number(value):
    if value in (None, ''):
        return ''
    return str(value).strip()


def url_tail(url):
    path = (url or '').split('#', 1)[0].split('?', 1)[0].rstrip('/')
    return path.rsplit('/', 1)[-1] if path else ''


def lookup_key(value):
    return str(value).strip().upper() if value else ''


class skyriverrvBrowse(scrapy.Spider):
    name = "skyriverrv"
    allowed_domains = ['skyriverrv.com']

    custom_settings = {
        # Feed + inventory API work from the droplet. Detail HTML is Vercel-limited
        # (429); those requests use Bright Data. API/feed set skip_proxy.
        'ENABLE_PROXY': True,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'RETRY_HTTP_CODES': [403, 429, 500, 502, 503, 504],
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_curl_cffi.handlers.CurlCffiDownloadHandler',
            'https': 'scrapy_curl_cffi.handlers.CurlCffiDownloadHandler',
        },
        'DOWNLOADER_MIDDLEWARES': {
            'Rocmob.middlewares.ProxyMiddleware': 100,
            'scrapy_curl_cffi.middlewares.CurlCffiMiddleware': 200,
            'scrapy_curl_cffi.middlewares.DefaultHeadersMiddleware': 400,
            'scrapy_curl_cffi.middlewares.UserAgentMiddleware': 500,
            'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': None,
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        },
        'CURL_CFFI_OPTIONS': {'impersonate': 'chrome131', 'timeout': 20},
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    }

    dealership_name = 'Sky River RV'
    dealer_type = 'RV'
    dealer_url = 'https://www.skyriverrv.com/'
    cms = 'Scout RV'
    location = ''  # used only when neither the API nor the detail page has a location

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_date = datetime.now(timezone.utc).date().isoformat()
        self.inserted_count = 0
        self.via_proxy_count = 0
        self.saved_without_location_count = 0
        self.units_by_key = {}

    def closed(self, reason):
        self.logger.info('Went through proxy: %s', self.via_proxy_count)
        self.logger.info('Saved without location: %s', self.saved_without_location_count)
        self.logger.info('Total inventory inserted: %s', self.inserted_count)

    def start_requests(self):
        yield scrapy.Request(
            INVENTORY_API_URL,
            callback=self.parse_inventory_api,
            errback=self.inventory_api_failed,
            dont_filter=True,
            meta={'skip_proxy': True},
        )

    def feed_request(self):
        return scrapy.Request(
            FEED_URL,
            callback=self.parse_feed,
            dont_filter=True,
            meta={'skip_proxy': True},
        )

    def inventory_api_failed(self, failure):
        self.logger.warning('Inventory API failed (%s); locations will come from detail pages', failure.value)
        yield self.feed_request()

    def parse_inventory_api(self, response):
        try:
            units = json.loads(response.text)
        except ValueError:
            self.logger.warning('Inventory API returned non-JSON (HTTP %s)', response.status)
            units = []

        for unit in units if isinstance(units, list) else []:
            loc = unit.get('location') or {}
            info = {
                'location': format_location(loc.get('city'), loc.get('state')),
                'dealership_address': format_address(
                    loc.get('address'), loc.get('city'), loc.get('state'), loc.get('zip')
                ),
                'dealership_phone': (loc.get('phone') or '').strip(),
                'stock_number': str(unit.get('stock_number') or '').strip(),
                'trim': (unit.get('trim') or '').strip(),
                'sleeps': clean_number(unit.get('sleeps')),
                'dry_weight': clean_number(unit.get('dry_weight_lbs') or unit.get('dry_weight')),
                'length': clean_number(unit.get('length_ft')),
            }
            for key in (
                unit.get('id'),
                unit.get('vin'),
                unit.get('slug'),
                unit.get('stock_number'),
                unit.get('name'),
            ):
                keyed = lookup_key(key)
                if keyed:
                    self.units_by_key[keyed] = info

        self.logger.info('Inventory API: %s units with location data', len(units) if isinstance(units, list) else 0)
        yield self.feed_request()

    def lookup_unit(self, *candidates):
        for key in candidates:
            keyed = lookup_key(key)
            if keyed and keyed in self.units_by_key:
                return self.units_by_key[keyed]
        return None

    def parse_feed(self, response):
        selector = Selector(text=response.text, type='xml')
        selector.remove_namespaces()
        vehicles = selector.xpath('//channel/item')
        self.logger.info('Found %s vehicles in the Google feed', len(vehicles))
        matched = 0

        for v in vehicles:
            def field(tag):
                return re.sub(r'\s+', ' ', v.xpath(f'./{tag}/text()').get() or '').strip()

            url = field('link')
            if not url:
                continue

            feed_id = field('id') or field('guid')
            vin = (field('vin') or field('mpn')).upper()
            slug = url_tail(url)
            raw_price = field('price').replace('USD', '').strip()

            mileage = field('mileage')
            mileage_parts = mileage.split()
            images = [field('image_link')] + [
                (img or '').strip() for img in v.xpath('./additional_image_link/text()').getall()
            ]

            item = {
                'url': url,
                'title': field('title'),
                'description': re.sub(r'<[^>]+>', '', html.unescape(field('description'))).strip(),
                'make': field('make') or field('brand'),
                'model': field('model'),
                'year': field('year'),
                'type_': field('vehicle_type'),
                'condition': field('condition').capitalize(),
                'price': '' if raw_price in ('', '0', '0.00') else raw_price,
                'vin': vin,
                'mileage_value': mileage_parts[0] if mileage_parts else '',
                'mileage_unit': mileage_parts[1] if len(mileage_parts) > 1 else '',
                'engine': field('engine'),
                'fuel_type': field('fuel_type').capitalize(),
                'transmission': field('transmission'),
                'custom_label_0': field('custom_label_0'),
                'custom_label_1': field('custom_label_1'),
                'custom_label_2': field('custom_label_2'),
                'images': [img for img in images if img][:3],
                'stock_number': slug.rsplit('-', 1)[-1].upper() if slug else '',
                'location': '',
                'dealership_address': '',
                'dealership_phone': '',
                'trim': '',
                'sleeps': '',
                'dry_weight': '',
                'length': '',
            }

            unit = self.lookup_unit(
                feed_id,
                vin,
                slug,
                item['stock_number'],
                item['title'],
                item['custom_label_0'],
                item['custom_label_1'],
                item['custom_label_2'],
            )
            if unit:
                matched += 1
                item.update({k: val for k, val in unit.items() if val})
                self.save_item(item)
            else:
                self.via_proxy_count += 1
                self.logger.info('Via proxy (%s): %s', self.via_proxy_count, url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    errback=self.detail_failed,
                    cb_kwargs={'item': item},
                    dont_filter=True,
                    meta={'download_timeout': 20},
                )

        self.logger.info(
            'Feed match: %s from inventory API, %s via proxy',
            matched,
            self.via_proxy_count,
        )

    def detail_failed(self, failure):
        item = (failure.request.cb_kwargs or {}).get('item')
        if not item:
            return
        retries = (failure.request.meta or {}).get('retry_times', 0)
        self.logger.warning(
            'Detail page failed for %s after %s retries (%s); saving without location as last resort',
            item.get('url'),
            retries,
            failure.value,
        )
        self.save_item(item)

    def parse_detail(self, response, item):
        text = response.text.replace('\\"', '"')
        match = DETAIL_LOCATION_RE.search(text)
        if match:
            block = match.group(1)

            def grab(key):
                found = re.search(rf'"{key}":"([^"]*)"', block)
                return found.group(1) if found else ''

            item['location'] = format_location(grab('city'), grab('state'))
            item['dealership_address'] = format_address(grab('address'), grab('city'), grab('state'), grab('zip'))
            item['dealership_phone'] = grab('phone')

        if not item['location']:
            badge = response.xpath(
                '//span[@data-slot="badge"][.//svg/path[starts-with(@d, "M15 11a3 3")]]//text()'
            ).getall()
            item['location'] = ' '.join(t.strip() for t in badge if t.strip())

        stock = response.xpath('//dt[normalize-space()="Stock Number"]/following-sibling::dd[1]/text()').get()
        if stock and stock.strip():
            item['stock_number'] = stock.strip()

        self.save_item(item)

    def save_item(self, item):
        url = item['url']
        title = item['title']
        stock_number = item['stock_number']
        vin = item['vin'] or stock_number
        location = item['location'] or self.location
        image_1, image_2, image_3 = (item['images'] + ['', '', ''])[:3]
        price = item['price']
        if price and not str(price).startswith('$'):
            price = f'${price}'

        try:
            sk = hashlib.md5(
                vin.encode('utf8') + title.encode('utf8') + url.encode('utf8')
            ).hexdigest()
        except Exception:
            sk = hashlib.md5(url.encode('utf8')).hexdigest()

        row = {
            'sk': sk,
            'dealership_name': self.dealership_name,
            'dealer_type': self.dealer_type,
            'dealership_address': item['dealership_address'],
            'dealership_phone': item['dealership_phone'],
            'store_code': '',
            'dealer_url': self.dealer_url,
            'cms': self.cms,
            'condition_': item['condition'],
            'year_': item['year'],
            'make': item['make'],
            'model': item['model'],
            'brand': item['model'],
            'vin': vin,
            'stock_number': stock_number,
            'url': url,
            'msrp': '',
            'price': price,
            'savings': '',
            'finance_option': '',
            'special_tag': '',
            'type_': item['type_'],
            'sub_type': '',
            'location': location,
            'image_url': image_1,
            'image_url_2': image_2,
            'image_url_3': image_3,
            'title': title,
            'description': item['description'],
            'trim': item['trim'],
            'length': item['length'],
            'doors': '',
            'drivetrain': '',
            'fuel_type': item['fuel_type'],
            'exterior_color': '',
            'interior_color': '',
            'sleeps': item['sleeps'],
            'seats': '',
            'dry_weight': item['dry_weight'],
            'mileage_value': item['mileage_value'],
            'mileage_unit': item['mileage_unit'],
            'engine': item['engine'],
            'transmission': item['transmission'],
            'body_style': '',
            'features': '',
            'custom_label_0': item['custom_label_0'],
            'custom_label_1': item['custom_label_1'],
            'custom_label_2': item['custom_label_2'],
            'creation_date': self.creation_date,
        }

        try:
            supabase.table('scrap_rawdata').upsert(
                row, on_conflict='sk,creation_date'
            ).execute()
            self.inserted_count += 1
            if not location:
                self.saved_without_location_count += 1
                self.logger.warning(
                    'Saved without location (%s): %s',
                    self.saved_without_location_count,
                    title,
                )
            else:
                self.logger.info('Upserted: %s', title)
        except Exception as db_err:
            self.logger.error('Supabase error for VIN %s: %s', vin, db_err)
