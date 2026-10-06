"""

Sky River RV spider (Scout RV Google feed):

  - vehicle data from the XML feed at /api/feeds/google (no pagination)

  - location from /api/inventory, /api/feeds/vla, or Google custom_label_0

  - leftover units use curl_cffi on the detail URL through the project default proxy from .env (no Playwright)

  - empty VIN falls back to stock number

  - upserts into Supabase scrap_rawdata

"""

import csv

import hashlib

import html

import io

import json

import re

from datetime import datetime, timezone

import scrapy

from scrapy.selector import Selector

from Rocmob.rocmob_cfg import supabase

BASE_URL = 'https://www.skyriverrv.com'

FEED_URL = f'{BASE_URL}/api/feeds/google'

VLA_FEED_URL = f'{BASE_URL}/api/feeds/vla'

INVENTORY_API_URL = f'{BASE_URL}/api/inventory'

DETAIL_LOCATION_RE = re.compile(r'"location":\\{"id":"[^"]+"(.*?)\\}', re.S)

LOT_LOCATION_RE = re.compile(

    r'(Atascadero|Paso Robles|Pismo Beach|Santa Maria|Fresno),?\s*CA',

    re.I,

)

PAGE_STOCK_RE = re.compile(r'Stock\s*#\s*([A-Za-z0-9-]+)', re.I)

CITY_STATE_RE = re.compile(r'^.+,\s*[A-Z]{2}$')

STOCK_LIKE_RE = re.compile(r'^[A-Z]{1,4}\d{2,}[A-Z0-9]*$', re.I)



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



def lot_location(value):

    text = (value or '').strip()

    if not text:

        return ''

    if CITY_STATE_RE.match(text):

        return text

    found = LOT_LOCATION_RE.search(text)

    return f'{found.group(1)}, CA' if found else ''



def xml_field(node, tag):

    raw = (

        node.xpath(f'./*[local-name()="{tag}"][1]/text()').get()

        or node.xpath(f'./{tag}/text()').get()

        or ''

    )

    return re.sub(r'\s+', ' ', raw).strip()



def xml_lot(node):

    for tag in (

        'custom_label_0',

        'custom_label_1',

        'custom_label_2',

        'custom_label_3',

        'custom_label_4',

    ):

        loc = lot_location(xml_field(node, tag))

        if loc:

            return loc

    return ''



class skyriverrvBrowse(scrapy.Spider):

    name = "skyriverrv"

    allowed_domains = ['skyriverrv.com']

    custom_settings = {
        # Keep Rocmob's project-level downloader middleware intact.
        # The working Clay Cooley spider relies on the project default proxy
        # configuration, including proxy credentials loaded from .env.
        # Do NOT replace DOWNLOADER_MIDDLEWARES here.
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'RETRY_HTTP_CODES': [500, 502, 503, 504],
        'HTTPERROR_ALLOWED_CODES': [429],
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_curl_cffi.handlers.CurlCffiDownloadHandler',
            'https': 'scrapy_curl_cffi.handlers.CurlCffiDownloadHandler',
        },
        'CURL_CFFI_OPTIONS': {'impersonate': 'chrome131'},
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

        self.via_detail_count = 0

        self.saved_without_location_count = 0

        self.units_by_key = {}

    def closed(self, reason):

        self.logger.info('Went through detail pages: %s', self.via_detail_count)

        self.logger.info('Saved without location: %s', self.saved_without_location_count)

        self.logger.info('Total inventory inserted: %s', self.inserted_count)

    def start_requests(self):

        yield scrapy.Request(

            INVENTORY_API_URL,

            callback=self.parse_inventory_api,

            errback=self.inventory_api_failed,

            dont_filter=True,


        )

    def vla_request(self):

        return scrapy.Request(

            VLA_FEED_URL,

            callback=self.parse_vla,

            errback=self.vla_failed,

            dont_filter=True,


        )

    def feed_request(self):

        return scrapy.Request(

            FEED_URL,

            callback=self.parse_feed,

            dont_filter=True,


        )

    def inventory_api_failed(self, failure):

        self.logger.warning('Inventory API failed (%s); trying VLA feed for locations', failure.value)

        yield self.vla_request()

    def vla_failed(self, failure):

        self.logger.warning('VLA feed failed (%s); locations will come from labels or detail pages', failure.value)

        yield self.feed_request()

    def _index_info(self, info, *keys):

        for key in keys:

            keyed = lookup_key(key)

            if not keyed:

                continue

            existing = self.units_by_key.get(keyed)

            if existing is None:

                self.units_by_key[keyed] = info

                continue

            for field, val in info.items():

                if val and not existing.get(field):

                    existing[field] = val

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

            self._index_info(

                info,

                unit.get('id'),

                unit.get('vin'),

                unit.get('slug'),

                unit.get('stock_number'),

                unit.get('name'),

            )

        self.logger.info('Inventory API: %s units with location data', len(units) if isinstance(units, list) else 0)

        yield self.vla_request()

    def parse_vla(self, response):

        try:

            rows = list(csv.DictReader(io.StringIO(response.text)))

        except Exception as exc:

            self.logger.warning('VLA feed was not CSV (%s)', exc)

            rows = []

        for row in rows:

            link = (row.get('link') or '').strip()

            info = {

                'location': lot_location(row.get('custom_label_0')),

                'dealership_address': '',

                'dealership_phone': '',

                'stock_number': (row.get('id') or '').strip(),

                'trim': (row.get('trim') or '').strip(),

                'sleeps': '',

                'dry_weight': '',

                'length': '',

            }

            if not info['location']:

                continue

            self._index_info(

                info,

                row.get('id'),

                row.get('vin'),

                url_tail(link),

                link,

            )

        self.logger.info('VLA feed: indexed %s rows with location', len(rows))

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

            url = xml_field(v, 'link')

            if not url:

                continue

            feed_id = xml_field(v, 'id') or xml_field(v, 'guid')

            vin = (xml_field(v, 'vin') or xml_field(v, 'mpn')).upper()

            slug = url_tail(url)

            raw_price = xml_field(v, 'price').replace('USD', '').strip()

            url_stock = slug.rsplit('-', 1)[-1].upper() if slug else ''

            stock_number = feed_id if STOCK_LIKE_RE.match(feed_id or '') else url_stock

            mileage = xml_field(v, 'mileage')

            mileage_parts = mileage.split()

            images = [xml_field(v, 'image_link')] + [

                (img or '').strip()

                for img in v.xpath('./*[local-name()="additional_image_link"]/text()').getall()

            ]

            item = {

                'url': url,

                'title': xml_field(v, 'title'),

                'description': re.sub(r'<[^>]+>', '', html.unescape(xml_field(v, 'description'))).strip(),

                'make': xml_field(v, 'make') or xml_field(v, 'brand'),

                'model': xml_field(v, 'model'),

                'year': xml_field(v, 'year'),

                'type_': xml_field(v, 'vehicle_type'),

                'condition': xml_field(v, 'condition').capitalize(),

                'price': '' if raw_price in ('', '0', '0.00') else raw_price,

                'vin': vin,

                'mileage_value': mileage_parts[0] if mileage_parts else '',

                'mileage_unit': mileage_parts[1] if len(mileage_parts) > 1 else '',

                'engine': xml_field(v, 'engine'),

                'fuel_type': xml_field(v, 'fuel_type').capitalize(),

                'transmission': xml_field(v, 'transmission'),

                'custom_label_0': xml_field(v, 'custom_label_0'),

                'custom_label_1': xml_field(v, 'custom_label_1'),

                'custom_label_2': xml_field(v, 'custom_label_2'),

                'images': [img for img in images if img][:3],

                'stock_number': stock_number,

                'location': xml_lot(v),

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

                stock_number,

                url_stock,

                item['title'],

                url,

            )

            if unit:

                item.update({k: val for k, val in unit.items() if val})

            if item['location']:

                matched += 1

                self.save_item(item)

            else:

                self.via_detail_count += 1

                self.logger.info('Via curl detail (%s): %s', self.via_detail_count, url)

                yield scrapy.Request(

                    url,

                    callback=self.parse_detail,

                    errback=self.detail_failed,

                    cb_kwargs={'item': item},

                    dont_filter=True,

                    meta={
                        'download_timeout': 30,
                        'detail_proxy_attempt': 1,
                    },

                )

        self.logger.info(

            'Feed match: %s with location, %s via curl detail pages',

            matched,

            self.via_detail_count,

        )

    def detail_failed(self, failure):
        item = (failure.request.cb_kwargs or {}).get('item')
        if not item:
            return

        self.logger.warning(
            'Detail request failed for %s (project default proxy): %s',
            item.get('url'),
            failure.value,
        )
        self.save_item(item)

    def parse_detail(self, response, item):
        if response.status == 429:
            attempt = int(response.request.meta.get('detail_proxy_attempt', 1))
            if attempt < 3:
                self.logger.warning(
                    'HTTP 429 on %s. Retrying detail page through proxy (attempt %s/3).',
                    response.url,
                    attempt + 1,
                )
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_detail,
                    errback=self.detail_failed,
                    cb_kwargs={'item': item},
                    dont_filter=True,
                    meta={
                        'download_timeout': 30,
                        'detail_proxy_attempt': attempt + 1,
                    },
                    headers={
                        'Referer': BASE_URL + '/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    },
                )
                return

            self.logger.error(
                'HTTP 429 after 3 detail attempts for %s; saving without location',
                response.url,
            )
            self.save_item(item)
            return

        self.logger.info(
            'Detail page HTTP %s via project default proxy: %s',
            response.status,
            response.url,
        )
        self.apply_detail_html(item, response.text)
        self.save_item(item)

    def apply_detail_html(self, item, html_text):

        selector = Selector(text=html_text)

        text = html_text.replace('\\\\"', '"')

        match = DETAIL_LOCATION_RE.search(text)

        if match:

            block = match.group(1)

            def grab(key):

                found = re.search(
                    rf'"{re.escape(key)}"\s*:\s*"([^"]*)"',
                    block
                )

                return found.group(1) if found else ''

            item['location'] = format_location(grab('city'), grab('state'))

            item['dealership_address'] = format_address(

                grab('address'), grab('city'), grab('state'), grab('zip')

            )

            item['dealership_phone'] = grab('phone')

        if not item['location']:

            badge = selector.xpath(

                '//span[@data-slot="badge"][.//svg/path[starts-with(@d, "M15 11a3 3")]]//text()'

            ).getall()

            item['location'] = (

                lot_location(' '.join(t.strip() for t in badge if t.strip()))

                or lot_location(text[:8000])

            )

        stock = selector.xpath(

            '//dt[normalize-space()="Stock Number"]/following-sibling::dd[1]/text()'

        ).get()

        if stock and stock.strip():

            item['stock_number'] = stock.strip()

        elif not item.get('stock_number') or not STOCK_LIKE_RE.match(item['stock_number']):

            found_stock = PAGE_STOCK_RE.search(text)

            if found_stock:

                item['stock_number'] = found_stock.group(1)

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