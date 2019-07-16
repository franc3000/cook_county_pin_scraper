# -*- coding: utf-8 -*-
# scrapy crawl propertyinfo -o properties.json -t jsonlines -L DEBUG
import scrapy
import re
from scrapy.spiders import CSVFeedSpider
from scrapy.exceptions import DropItem
from collections import OrderedDict
from cook_county_pin_scraper.items import Property
from cook_county_pin_scraper.custom_filters import CustomFilter

class PropertyinfoSpider(CSVFeedSpider):
    headers = ['pin']
    name = "propertyinfo"
    allowed_domains = ["cookcountypropertyinfo.com"]
    start_urls = [
        #"file:///Users/stevevance/Sites/cook_county_pin_scraper/lists/batch12.csv"
        #"file:///Users/stevevance/Sites/cook_county_pin_scraper/lists/sample.csv"
        "http://chicagocityscape.com/scrapy/batch11.csv"
    ]
    state = OrderedDict()

    def parse_row(self, response, row):
        pin = row['pin']
        url = "http://www.cookcountypropertyinfo.com/cookviewerpinresults.aspx?pin="+pin
        #url = "file:///Users/stevevance/Sites/cook_county_pin_scraper/cook_county_pin_scraper/test.html"
        return scrapy.Request(url, callback=self.parse_pin)

    def extract_with_prefix(self, response, suffix, inner_part=''):
        ext = response.xpath('//*[@id="ContentPlaceHolder1_{}"]{}/text()'.format(suffix, inner_part))
        if len(ext) == 1:
            return ext[0].extract()
        else:
            return None

    def parse_pin(self, response):
        item = Property()
	    
        # If there's a DIV with the ID of ContentPlaceHolder1_failure, then skip this item.
        if response.xpath('//*[@id="ContentPlaceHolder1_failure"]'):
            raise DropItem("Item contained 'failure' DIV")

        self.state['items_count'] = self.state.get('items_count', 0) + 1
        
        # Check for a PIN; if none, skip this PIN and don't create a record for it
        item['pin'] = self.extract_with_prefix(response, 'lblResultTitle')
        if item['pin']:
	        item['pin14'] = re.sub('[^0-9]+', '', item['pin'])
        else:
	        yield None

        # Create the property_tax_year
        property_tax_year = self.extract_with_prefix(response, "TaxBillInfo_rptTaxBill_taxBillYear_0")
        if property_tax_year:
            property_tax_year = int(re.sub('[^0-9]+', '', property_tax_year))
        item['property_tax_year'] = property_tax_year
        
        item['address'] = self.extract_with_prefix(response, 'PropertyInfo_propertyAddress')
        item['city'] = self.extract_with_prefix(response, 'PropertyInfo_propertyCity')
        item['zip_code'] = self.extract_with_prefix(response, 'PropertyInfo_propertyZip')
        item['township'] = self.extract_with_prefix(response, 'PropertyInfo_propertyTownship')
        
        estimated_property_value = self.extract_with_prefix(response, 'TaxYearInfo_propertyEstimatedValue')
        if estimated_property_value: 
            item['estimated_property_value'] = float(estimated_property_value.replace('$', '').replace(',',''))
        else:
            item['estimated_property_value'] = -1
            
        total_assessed_value = self.extract_with_prefix(response, 'TaxYearInfo_propertyAssessedValue')
        if total_assessed_value: 
            item['total_assessed_value'] = float(total_assessed_value.replace('$', '').replace(',',''))
        else:
            item['total_assessed_value'] = -1
            
        # Which assessment pass is this?
        item['assessment_pass'] = self.extract_with_prefix(response, 'TaxYearInfo_propertyAssessorPass')
        if item['assessment_pass']:
            item['assessment_pass'] = item['assessment_pass'].strip("()")
        
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

        # Make the Mailing Address
        mailing_name = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingName')
        mailing_address = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingAddress')
        mailing_city_state_zip = self.extract_with_prefix(response, 'PropertyInfo_propertyMailingCityStateZip')
        item['mailing_address'] = OrderedDict([
            ('year', property_tax_year),
            ('name', mailing_name),
            ('address', mailing_address),
            ('city_state_zip', mailing_city_state_zip),
        ])

        # Make YEARS - 0,5 means grab the current year and 4 more years (5 years); 1,4 means grab the second year, and 3 more years (4 years)
        years = OrderedDict()
        
        # Make Tax History
        for i in range(0, 5):
            bill_year = self.extract_with_prefix(response, 'TaxBillInfo_rptTaxBill_taxBillYear_{}'.format(i))
            if bill_year:
                bill_year = bill_year.replace(':', '')
                bill_year = int(bill_year)
                
            bill_amount = self.extract_with_prefix(response, 'TaxBillInfo_rptTaxBill_taxBillAmount_{}'.format(i))
            if bill_amount:
                bill_amount = float(bill_amount.replace('$', '').replace(',', ''))

            years[bill_year] = {
	            'year': bill_year,
                'bill': bill_amount
            }

            # these are all optional
            bill_exemption = response.xpath('//div[@id="ContentPlaceHolder1_TaxBillInfo_rptTaxBill_Panel5_{}"]/div[@class="pop2Display"]/a/span/text()'.format(i)).extract()
            if bill_exemption:
			    years[bill_year]['exempt'] = 'Exempt PIN'
			    item['status'] = 'exempt'

            not_available = response.xpath('//div[@id="ContentPlaceHolder1_TaxBillInfo_rptTaxBill_Panel6_{}"]/div[@class="pop2Display"]/a/span/text()'.format(i)).extract()
            if not_available:
			    years[bill_year]['not_available'] = 'Not Available'

            divided_pin = response.xpath('//div[@id="ContentPlaceHolder1_TaxBillInfo_rptTaxBill_Panel4_{}"]/div[@class="pop2Display"]/a/span/text()'.format(i)).extract()
            if divided_pin:
			    years[bill_year]['divided_pin'] = 'Divided PIN'

        # Do TAX ASSESSMENTS
        tax_assessments = response.xpath('//div[@id="assesspop2"]/div[@class="modal-body2"]/table/tr')
        for row in tax_assessments:
            year, assessed_value = row.xpath('td/text()').extract()
            year = int(year.strip())
            assessed_value = int(assessed_value.replace(',', ''))
            years[year]['assessment'] = assessed_value
        
        # Do TAX RATES
        tax_rates_text = []
        tax_rates_table = response.xpath('//table[@id="taxratehistorytable"]/tr')
        
        # remove the first item in tax_rates_text aray because it's a paragraph and not a tax rate
        if len(tax_rates_table) > 0:
            tax_rates_table.pop(0)
        
        # iterate the tax rates
        for row in tax_rates_table:
            cells = row.xpath('td/text()').extract()
            cell = {
            	'year': re.sub('[^A-Za-z0-9]+', '', cells[0]),
            	'tax_rate': re.sub('[^A-Za-z0-9.]+', '', cells[1])
            }
            tax_rates_text.append(cell)

        # parse the tax_rates_text and assign the tax rates to the year array
        for row in tax_rates_text:
            #splitted = re.split("<span.*</span>", text)
            year = int(row['year'])
            tax_rate = float(row['tax_rate'])
            years[year]['tax_rate'] = tax_rate
            
        # exemption and appeal history  
        exemptions = OrderedDict()
        for year, attrs in years.items():

            #exemption_status = response.xpath('//*[@id="exemption{}-button"]/span/text()'.format(year) )
            exemption_result = response.xpath('//*[@id="exemption{}-popup"]/div[1]/text()'.format(year) )
            
            if exemption_result:
                exemptions[year] = exemption_result[1].extract().strip()
                years[year]['exemption'] = exemptions[year]
            else:
                exemptions[year] = None
                
        item['exemptions'] = exemptions
        
        # appeals
        appeals = OrderedDict()
        for year, attrs in years.items():

            appeal_filed = response.xpath('//*[@id="appealfilednotaccepting2{}-button"]/span/text()'.format(year) )
            appeal_not_being_accepted = response.xpath('//*[@id="appealsnotaccepting2{}-button"]/span/text()'.format(year) )
            
            status = None
            if appeal_filed:
                status = appeal_filed[0].extract().strip()
            
            if appeal_not_being_accepted:
                status = appeal_not_being_accepted[0].extract().strip()
                
            appeals[year] = status
            years[year]['appeals'] = appeals[year]
                
        item['appeals'] = appeals
        
        # Do TAX CODES (after getting property_tax_year)
        tax_code = self.extract_with_prefix(response, 'TaxYearInfo_propertyTaxCode')
        # sometimes the tax_code_year is not contained in the years item from Tax Assessments so we must set an empty array for it
        if not years[property_tax_year]:
            years[property_tax_year] = {}
        years[property_tax_year]['tax_code'] = tax_code
        
        # Create the final "years", or tax_history array
        item['tax_history'] = []
        for year, attrs in years.items():
            year_dict = dict(year=year)
            year_dict.update(attrs)
            item['tax_history'].append(year_dict)

        yield item
