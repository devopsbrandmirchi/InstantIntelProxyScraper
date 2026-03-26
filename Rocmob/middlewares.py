# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter
import base64
import random
from scrapy.utils.project import get_project_settings
import requests

class RocmobSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class RocmobDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
class ProxyMiddleware(object):
    def __init__(self, enabled, proxy_url, proxy_auth_list):
        self.enabled = enabled
        self.proxy_url = proxy_url
        self.proxy_auth_list = proxy_auth_list

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        mw = cls(
            enabled=settings.getbool("ENABLE_PROXY", True),
            proxy_url=settings.get("PROXY_URL", "").strip(),
            proxy_auth_list=settings.getlist("HTTP_PROXY"),
        )
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        if not self.enabled:
            spider.logger.info(
                "ProxyMiddleware: proxy disabled (ENABLE_PROXY=false); outbound requests are direct."
            )
            return
        if not self.proxy_url:
            spider.logger.warning(
                "ProxyMiddleware: proxy enabled but PROXY_URL is empty; outbound requests are direct."
            )
            return
        if len(self.proxy_auth_list) > 1:
            auth_note = "with Proxy-Authorization (rotating credentials)"
        elif len(self.proxy_auth_list) == 1:
            auth_note = "with Proxy-Authorization (single credential from PROXY_AUTH)"
        else:
            auth_note = "without credentials (no PROXY_AUTH / PROXY_AUTH_LIST)"
        spider.logger.info(
            "ProxyMiddleware: proxy enabled for spider %r; endpoint %s; %s",
            spider.name,
            self.proxy_url,
            auth_note,
        )

    def process_request(self, request, spider):
        if request.meta.get("skip_proxy"):
            request.meta.pop("proxy", None)
            request.headers.pop("Proxy-Authorization", None)
            return

        if not self.enabled:
            return

        if not self.proxy_url:
            spider.logger.warning("ENABLE_PROXY is true but PROXY_URL is empty; request sent without proxy.")
            return

        request.meta["proxy"] = self.proxy_url
        if self.proxy_auth_list:
            auth_creds = random.choice(self.proxy_auth_list)
            access_token = base64.b64encode(auth_creds.encode("utf-8")).decode("utf-8")
            request.headers["Proxy-Authorization"] = f"Basic {access_token}"
