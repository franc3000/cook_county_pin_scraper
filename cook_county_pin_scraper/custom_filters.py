import os

from scrapy.dupefilters import RFPDupeFilter
from scrapy.utils.request import request_fingerprint


class CustomFilter(RFPDupeFilter):
    """A dupe filter that considers specific ids in the url"""

    def __getid(self, url):
        mm = url.split("=")[1]
        return mm

    def request_seen(self, request):
        # fp = self.__getid(request.url)
        # if fp in self.fingerprints:
        #     return True
        # self.fingerprints.add(fp)
        # if self.file:
        #     self.file.write(fp + os.linesep)
        return False
