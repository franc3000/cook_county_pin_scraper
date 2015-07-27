# -*- coding: utf-8 -*-

# Scrapy settings for cook_county_pin_scraper project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'cook_county_pins'

SPIDER_MODULES = ['cook_county_pin_scraper.spiders']
NEWSPIDER_MODULE = 'cook_county_pin_scraper.spiders'
DOWNLOAD_DELAY = 0.035
CONCURRENT_REQUESTS = 1
MEMDEBUG_ENABLED = True
#MEMDEBUG_NOTIFY = ['jamesbondsv@gmail.com']

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'cook_county_pin_scraper (+http://www.yourdomain.com)'
