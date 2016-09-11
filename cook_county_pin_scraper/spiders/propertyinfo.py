# -*- coding: utf-8 -*-
import scrapy
import re
from scrapy.spiders import CSVFeedSpider
from collections import OrderedDict
from cook_county_pin_scraper.items import Property
from cook_county_pin_scraper.custom_filters import CustomFilter

class PropertyinfoSpider(CSVFeedSpider):
    headers = ['pin']
    name = "propertyinfo"
    allowed_domains = ["cookcountypropertyinfo.com"]
    start_urls = [
    	"file:///cook_county_pin_scraper/lists/8.txt"
    ]
    state = OrderedDict()

    def parse_row(self, response, row):
        pin = row['pin']
        return scrapy.Request('http://www.cookcountypropertyinfo.com/cookviewerpinresults.aspx?pin='+pin, callback=self.parse_pin)

    def extract_with_prefix(self, response, suffix, inner_part=''):
        ext = response.xpath('//span[@id="ContentPlaceHolder1_{}"]{}/text()'.format(suffix, inner_part))
        if len(ext) == 1:
            return ext[0].extract()
        else:
            return None

    def parse_pin(self, response):
        if self.extract_with_prefix(response, 'resultsNotFoundPanel'):
            yield None
            
        self.state['items_count'] = self.state.get('items_count', 0) + 1

        item = Property()

        item['property_tax_year'] = self.extract_with_prefix(response, 'TaxYearInfo_assessmentTaxYear2')
        if item['property_tax_year'][-4:].isnumeric():
            item['property_tax_year'] = int(item['property_tax_year'][-4:])
        else:
            item['property_tax_year'] = -1

        item['pin'] = self.extract_with_prefix(response, 'lblResultTitle')
        item['address'] = self.extract_with_prefix(response, 'PropertyInfo_propertyAddress')
        item['city'] = self.extract_with_prefix(response, 'PropertyInfo_propertyCity')
        item['zip_code'] = self.extract_with_prefix(response, 'PropertyInfo_propertyZip')
        item['township'] = self.extract_with_prefix(response, 'PropertyInfo_propertyTownship')
        
        estimated_property_value = self.extract_with_prefix(response, 'TaxYearInfo_propertyEstimatedValue')
        if estimated_property_value: 
            item['estimated_property_value'] = float(estimated_property_value.replace('$', '').replace(',',''))
        else:
            item['estimated_property_value'] = None
            
        total_assessed_value = self.extract_with_prefix(response, 'TaxYearInfo_propertyAssessedValue')
        if total_assessed_value: 
            item['total_assessed_value'] = float(total_assessed_value.replace('$', '').replace(',',''))
        else:
            item['total_assessed_value'] = None
        
        item['lot_size'] = self.extract_with_prefix(response, 'TaxYearInfo_propertyLotSize')
        if item['lot_size']:
            item['lot_size'] = int(item['lot_size'].replace(',', ''))

        item['building_size'] = self.extract_with_prefix(response, 'TaxYearInfo_propertyBuildingSize')
        if item['building_size']:
            item['building_size'] = int(item['building_size'].replace(',', ''))

        property_class_description = self.extract_with_prefix(response, 'TaxYearInfo_msgPropertyClassDescription2')
        if property_class_description:
            property_class_description = self.extract_with_prefix(response, 'TaxYearInfo_msgPropertyClassDescription2')
        else:
            property_class_description = None

        item['property_class'] = {
            'class': self.extract_with_prefix(response, 'TaxYearInfo_propertyClass'),
            'description': property_class_description
        }
        
        building_age = self.extract_with_prefix(response, 'propertyBuildingAge')
        if building_age:
            item['building_age'] = building_age
        else:
            item['building_age'] = None
        # building age isn't there as of 2015 tax year

        mailing_tax_year = self.extract_with_prefix(response, 'mailingTaxYear', '/b')
        if mailing_tax_year:
            mailing_tax_year = int(mailing_tax_year[-4:])
        # mailing tax year isn't there as of 2015 tax year
        mailing_name = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingName')
        mailing_address = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingAddress')
        mailing_city_state_zip = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingCityStateZip')
        item['mailing_address'] = OrderedDict([
            ('year', mailing_tax_year),
            ('name', mailing_name),
            ('address', mailing_address),
            ('city_state_zip', mailing_city_state_zip),
        ])

        # Make YEARS
        years = OrderedDict()
        for i in range(0, 5):
            bill_year = self.extract_with_prefix(response, 'TaxBillInfo_rptTaxBill_taxBillYear_{}'.format(i))
            if bill_year:
                bill_year = bill_year.replace(':', '')
                bill_year = int(bill_year)
            bill_amount = self.extract_with_prefix(response, 'TaxBillInfo_rptTaxBill_taxBillAmount_{}'.format(i))
            if bill_amount:
                bill_amount = float(bill_amount.replace('$', '').replace(',', ''))

            years[bill_year] = {
                'bill': bill_amount
            }

            bill_exemption = response.xpath('//div[@id="ContentPlaceHolder1_TaxBillInfo_rptTaxBill_Panel5_{}"]/div[@class="pop2Display"]/a/span/text()'.format(i))
            if bill_exemption:
			    years[year]['exempt'] = bill_exemption

            not_available = response.xpath('//div[@id="ContentPlaceHolder1_TaxBillInfo_rptTaxBill_Panel6_{}"]/div[@class="pop2Display"]/a/span/text()'.format(i))
            if not_available:
			    years[year]['not_available'] = not_available

        # Do TAX ASSESSMENTS
        for row in response.xpath('//div[@id="assesspop2"]/div[@class="modal-body2"]/table/tr'):
            year, assessed_value = row.xpath('td/text()').extract()
            year = int(year.strip())
            assessed_value = int(assessed_value.replace(',', ''))
            years[year]['assessment'] = assessed_value

        # Do TAX CODES
        tax_code_year = int(self.extract_with_prefix(response, 'TaxYearInfo_taxCodeTaxYear')[1:5])
        tax_code = self.extract_with_prefix(response, 'TaxYearInfo_propertyTaxCode')
        # sometimes the tax_code_year is not contained in the years item from above so we must set an empty array for it
        if tax_code_year not in years:
            years[tax_code_year] = {}
        years[tax_code_year]['tax_code'] = tax_code
        
        # Do TAX RATES
        tax_rates_text = []
        #tax_rates_text.append("this text should be removed")
        #tax_rates_text.append("2014 <span>text</span> 6.554")

        for row in response.xpath('//table[@id="taxratehistorytable"]/tr'):
            text = row.xpath('td/text()').extract()
            tax_rates_text.append(text)
            
        # remove the first item in tax_rates_text because it's a paragraph
        tax_rates_text.pop(0)
        for year, text in tax_rates_text:
            #splitted = re.split("<span.*</span>", text)
            year = int(year.strip())
            tax_rate = float(text.strip())
            years[year]['tax_rate'] = tax_rate

        item['tax_history'] = []
        for year, attrs in years.items():
            year_dict = dict(year=year)
            year_dict.update(attrs)
            item['tax_history'].append(year_dict)

        yield item
