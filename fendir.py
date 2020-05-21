import os, json, re, statistics, urllib3
import requests as r
from flask import Flask, request, jsonify
from sklearn.cluster import KMeans
import numpy as np
import brotli # looks unused but requests needs it to decipher Carousell return data

app = Flask(__name__)
urllib3.disable_warnings()

'''
Product classes used to store data for individual products or listings
from both Reverb and Carousell. TODO: remove base class?
'''
class Product(object):
    def __init__(self):
        self.title = ""
        self.price = -1
        self.description = ""
        self.new_or_used = ""

class CarousellProduct(Product): 
    def __init__(self):
        super(Product, self).__init__()
        self.likes = ""

    def fetch_product_data(self, search_listing_json):
        '''
        Extracts listing ID from search results, requests Carousell's API
        for that specific listing info, and then uses it to load the product. 
        '''

        product_id = search_listing_json['listingCard']['id']

        headers = {
            'authority': 'sg.carousell.com',
            'y-platform': 'web',
            'y-accept-language': 'en',
            'y-build-no': '2',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
            'content-type': 'application/json',
            'accept': '*/*',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'referer': 'https://sg.carousell.com/p/fender-japan-strat-272425486?t-id=3755337_1577951790910&t-referrer_browse_type=search_results&t-referrer_request_id=Zc9-YP7SjnULa_ms&t-referrer_search_query=fender&t-referrer_sort_by=popular',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en,en-US;q=0.9,ms;q=0.8',
            'cookie': '__cfduid=db5ce03256b89cd9bf2180e8ce47ac8001548561275; ffid=sp2ikhIC7-p9DhYe; backend_feature_flag_id=tex7sjdjJAbPl8GfipzHUpZ23Yj8DuZQhBVc; gtkprId=mPigJCYio95zIMTk; _csrf=38VmEktJ2Hbzt4_FlmtoTlK6; _t2=cmyT-Ahsp0; __stripe_mid=0917a744-d1e5-4d68-9d3e-cb5f77ccec31; redirect=redirect; akamaru_session=51GgQy4sL45KMOazoiFKAcTUqooCd6vMhjBz; auth-session=51GgQy4sL45KMOazoiFKAcTUqooCd6vMhjBz; _t=t%3D1577951790910%26u%3D3755337; cf_use_ob=0; latra=1578787200000',
            'if-none-match': 'W/"3bbe-0OodRBk3jtomFlIGV2EvDrqFcwE"',
        }

        response = r.get('https://sg.carousell.com/api-service/listing/3.1/listings/{}/detail/'.format(product_id), headers=headers, verify=False)

        j = json.loads(response.text)
        # print(j['data'])
        self.load_from_json(j)


    def load_from_json(self, json_object):
        self.title = json_object['data']['screens'][0]['meta']['default_value']['title']
        self.price = float(json_object['data']['screens'][0]['meta']['default_value']['price'])
        self.description = json_object['data']['screens'][0]['meta']['default_value']['description']
        self.is_popular = json_object['data']['screens'][0]['meta']['default_value']['is_popular']
        self.likes = int(json_object['data']['screens'][0]['meta']['default_value']['likes_count'])
        self.url = re.search("(?P<url>https?://[^\s]+)", json_object['data']['screens'][0]['meta']['share_text']).group("url")

class ReverbProduct(Product): 
    def __init__(self):
        super(Product, self).__init__()

    def load_from_json(self, json_object):
        self.id = json_object['id']
        self.make = json_object['make'].strip()
        self.model = json_object['model'].strip()
        self.finish = json_object['finish'].strip()
        self.year = json_object['year']
        self.title = json_object['title'].strip()
        self.description = json_object['description'].strip()
        self.condition = json_object['condition']
        self.price = round(float(json_object['price']['amount']) * 1.35, 2) # convert from USD to SGD and round to 2 d.p.
        self.buyer_price = json_object['buyer_price']
        self.inventory = json_object['inventory']
        self.has_inventory = json_object['has_inventory']
        self.listing_currency = json_object['listing_currency']
        self.state = json_object['state']
        self.categories = [x['full_name'] for x in json_object['categories']]
        self.links = json_object['_links']

'''
Search classes for Carousell and Reverb work slightly differently owing 
to the underlying platform differences (so no common base class). 
'''

class CarousellSearch():
    '''
    This is the class for a Carousell search. Every search should have its own instance.
    There are several functions to assist with development, and they start with an
    underscore. Carousell is a lot more finicky than Reverb so additional keyword tweaking
    and exclusion might be needed to get a good result. 

    EX:
    a = CarousellSearch("fender stratocaster", additional_filters={"brand": "fender", "model": "stratocaster"})
    a.find_undervalued_listings()
    '''

    def __init__(self, query_string=None, additional_filters={'brand': ''}, search_params={'number_of_results': 22, 'number_of_pages': 3}, 
        debug_keys={'using_local': False, 'print_links': False, 'print_histogram': False}):
        self.products = []

        self.debug_keys = debug_keys
        self.search_params = search_params

        self.query = query_string
        self.color = additional_filters['color'] if 'color' in additional_filters.keys() else None
        self.brand = additional_filters['brand']

        self.prices = None
        self.mean_price = None

        headers = {
            'Host': 'sg.carousell.com',
            'Connection': 'close',
            'Content-Length': '110',
            'y-X-Request-ID': 'QQCiHsizJ2MsUbsT',
            'Origin': 'https://sg.carousell.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Referer': 'https://sg.carousell.com/search/fender%20black%20stratocaster',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en,en-US;q=0.9,ms;q=0.8',
        }

        data = {
            "count": self.search_params['number_of_results'], 
            "countryId": "1880251",
            "filters": [{"fieldName":"collections","idsOrKeywords":{"value":["233"]}}],
            "locale": "en",
            "prefill": {}, 
            "query": self.query
        }

        response = r.post('https://sg.carousell.com/api-service/filter/search/3.3/products/', headers=headers, data=json.dumps(data), verify=False)

        self.returned_json = json.loads(response.text)
        self.product_list = self.returned_json['data']['results']
        self.valid_product_list = self.validate_all_listings()
        
    def find_undervalued_listings(self):
        '''
        Finds all listings below average price and prints them in ascending
        order of price. 

        Returns nothing but has print output. 
        '''

        below_average_listings = [p for p in self.valid_product_list if p.price < (self.mean_price)]
        sorted_below_average_listings = sorted(below_average_listings, key=lambda k: k.price) 

        print("=" * 25)
        print("AVERAGE PRICE: ${}".format(self.mean_price))
        print("-" * 25)
        print("LISTINGS BELOW AVERAGE:")
        print("=" * 25)

        for product in sorted_below_average_listings:
            if product.price < (self.mean_price): print(product.title, ": ", product.price, "({})".format(product.url))

    def validate_all_listings(self):
        '''
        Return an array of all the valid listings received from Carousell. Works
        as follows: loads all listings from JSON into custom CarousellProduct 
        class from above -> filters individual listings using self.is_listing_valid()
        -> TODO (strip too cheap to remove e.g "squire") -> return valid listings.

        Returns array of valid listings. 
        '''

        # first pass: remove the majority of BS listings
        first_pass = []
        prices = []
        for product_json in self.product_list:
            product = CarousellProduct()
            product.fetch_product_data(product_json)

            if not self.is_listing_valid(product):
                continue # skip all fake entries

            first_pass.append(product)
            prices.append(product.price)

        self.prices = prices
        self.mean_price = round(statistics.mean(self.prices), 2)
        
        return first_pass

    def is_listing_valid(self, product_object):
        '''
        Function for filtering irrelevant listings. Category and color have a nonstandard 
        validation so they get their own clauses. The rest in `custom_validation` use 
        simple string matching in the description.

        Returns True if valid, False if not. 
        '''
        # 0 price removal
        if product_object.price == 0: return False

        # brand filtering
        brands = ["Gibson", "Fender", "PRS", "G&L", "Rickenbacker", "Ibanez", "ESP", "Jackson", "Schecter", "Epiphone", "Martin", "Taylor", "Guild", "Seagull", "Yamaha", "Ovation", "Washburn"]
        for word in product_object.title.split(" "):
            if word in brands:
                if word.lower().strip() != self.brand.lower().strip(): return False

        # is valid if no error caught before
        return True

    def generate_histogram(self, data, xlabel, ylabel, title):
        '''
        DEPRECATED. Generates histogram of prices using matplotlib. Sample
        usage: self.generate_histogram(prices, "Price", "Frequency", "Price/Frequency Histogram: {}".format(self.query))
        Taken from: https://realpython.com/python-histograms/.

        Returns nothing but displays figure. 
        '''

        n, bins, patches = plt.hist(x=data, bins='auto', color='#0504aa',
                                    alpha=0.7, rwidth=0.85)
        plt.grid(axis='y', alpha=0.75)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.text(23, 45, r'$\mu=15, b=3$')
        maxfreq = n.max()
        # Set a clean upper y-axis limit.
        plt.ylim(ymax=np.ceil(maxfreq / 10) * 10 if maxfreq % 10 else maxfreq + 10)
        plt.show()
   
class ReverbSearch():
    '''
    This is the class for a Reverb search. Every search should have its own instance.
    There are several functions to assist with development, and they start with an
    underscore. TODO: copy function structure (e.g. find_undervalued_listings) from
    Carousell. 

    EX: 
    ReverbSearch("fender stratocaster", number_of_results=50, number_of_pages=5, 
        additional_filters={'color': 'sunburst'}, 
        debug_keys={'using_local': True, 'print_links': True, 'print_histogram': False}).calculate_avg_price()
    '''
    def __init__(self, query_string=None, additional_filters={}, search_params={'number_of_results': 22, 'number_of_pages': 3}, print_links=False,
        debug_keys={'using_local': False, 'write_local': False, 'print_histogram': False, 'verbose': False}):
        '''
        The constructor is responsible for scraping the list of products for a given query, 
        and initialising appropriate instance variables. It does NOT find the undervalued 
        listings.
        '''
        self.products = []

        self.debug_keys = debug_keys
        self.print_links = print_links
        self.search_params = search_params

        self.query = query_string
        self.color = additional_filters['color'] if 'color' in additional_filters.keys() else None

        self.session = r.session()

        payload = additional_filters
        payload['query'] = self.query
        if 'number_of_results' in search_params.keys(): payload['per_page'] = search_params['number_of_results']

        if self.debug_keys['write_local']:
            f = open("cached_product_list", "w")
            f.write(str(self.product_list))
            f.close()

        if self.debug_keys['using_local']:
            if debug_keys['verbose']: print("USING LOCAL CACHE")
            self.product_list = eval(open("cached_product_list", "r").read())
        else:
            if debug_keys['verbose']: print("USING LIVE DATA")

            # DOCS: https://www.any-api.com/reverb_com/reverb_com/docs/_listings_all/GET
            response = self.session.get('https://api.reverb.com/api/listings/all', headers={'Accept-Version': "3.0"}, params=payload).text
            returned_json = json.loads(response)
            self.product_list = returned_json['listings']

            count = 0
            while 'next' in returned_json['_links'] and count < search_params['number_of_pages']:
                response = self.session.get(returned_json['_links']['next']['href'], headers={'Accept-Version': "3.0"}).text
                try:
                    returned_json = json.loads(response)
                except TypeError as e:
                    print(response, response.text)
                    raise e
                self.product_list.extend(returned_json['listings'])
                count += 1

    def find_undervalued_listings(self):
        '''
        This function filters out listings using `self.is_listing_valid()` and then
        calculates an average price. Prints appropriate info and generates histogram
        if the flag says to. 
        '''
        sum = 0
        count = 0
        prices = []

        for p_itr in self.product_list:
            p = ReverbProduct()
            p.load_from_json(p_itr)

            validation_checks = {}

            if not self.is_listing_valid(p, custom_validation=validation_checks): continue

            self.products.append(p)
            prices.append(p.price)
            sum += p.price
            count += 1

        below_average_listings = [p for p in self.products if p.price < (sum/count)]
        sorted_below_average_listings = sorted(below_average_listings, key=lambda k: k.price) 

        print("=" * 25)
        print("AVERAGE PRICE: ${}".format(round(sum/count, 2)))
        print("-" * 25)
        print("LISTINGS BELOW AVERAGE:")
        print("=" * 25)
        for product in sorted_below_average_listings:
            
            if product.price < (sum/count):
                # TODO: use tabs to make this print prettier
                o = product.title + ": " + str(product.price)
                if self.print_links: o += " ({})".format(product.links['web']['href'])
                print(o)

        if self.debug_keys['print_histogram'] == True: 
            import matplotlib.pyplot as plt # conditionally import b/c it slows down a lot otherwise
            self.generate_histogram(prices, "Price", "Frequency", "Price/Frequency Histogram: {}".format(self.query))

    def is_listing_valid(self, product_object, custom_validation=None):
        '''
        Function for filtering irrelevant listings. Category and color have a nonstandard 
        validation so they get their own clauses. The rest in `custom_validation` use 
        simple string matching in the description.
        '''

        # category validation
        valid_category = False
        for category in product_object.categories:
            if "Electric Guitars" in category:
                valid_category = True
        if not valid_category: return False

        # color validation
        # are there a finite amount of colors? make an array and search to make sure rest aren't in desc. if so

        if self.color:
            if product_object.finish == "": 
                if self.color not in product_object.description.lower(): return False
            else:
                # can be more robust: strip whitespace?
                if self.color not in product_object.finish.lower(): return False

        # is valid if no error caught before — no custom validation
        if not custom_validation: return True

        # custom validation
        ''' ALL LOWERCASE
        {'place_of_manufacturing': ['made in mexico', 'mim'], 'year_manufactured': ['2012']}
        '''

        for validation_label in custom_validation:
            print("performing custom validation!")
            # iterates through each variation of keyphrase (e.g. 'made in mexico', 'mim') and
            # then if at least one is found, then it's validated, so we toggle the flag appropriately
            validated = False
            for phrase in custom_validation[validation_label]:
                if phrase in product_object.description or phrase in product_object.title: validated = True
            if not validated: return False

        # is valid if no error caught before
        return True

    def generate_histogram(self, data, xlabel, ylabel, title):
        '''
        Generates a histogram of an array of `data`, which we assume is of prices. 
        '''
        # https://realpython.com/python-histograms/
        n, bins, patches = plt.hist(x=data, bins='auto', color='#0504aa',
                                    alpha=0.7, rwidth=0.85)
        plt.grid(axis='y', alpha=0.75)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.text(23, 45, r'$\mu=15, b=3$')
        maxfreq = n.max()
        # Set a clean upper y-axis limit.
        plt.ylim(ymax=np.ceil(maxfreq / 10) * 10 if maxfreq % 10 else maxfreq + 10)
        plt.show()

    def _print_single_listing_json(self):
        '''
        Prints first item in product_list array. For development, when the JSON for a single
        listing is required
        '''
        print(self.product_list[0])


# ReverbSearch("fender stratocaster HSS floyd rose", search_params={'number_of_results':50, 'number_of_pages':3}, 
#     additional_filters={'neck_material': ['maple'], 'color': 'sunburst'}).find_undervalued_listings()

# CarousellSearch("fender stratocaster", additional_filters={"brand": "fender", "model": "stratocaster", "color": "black"}).find_undervalued_listings()

# CarousellSearch("charvel san dimas", additional_filters={"brand": "charvel", "model": "san dimas"}).find_undervalued_listings()
# a.find_undervalued_listings()
# print(a.valid_product_list)
