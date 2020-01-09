'''
todos:
- add ability get more than 50 items (currently maxes out then)
- add better searching logic: specify search object (includes color, make, manufacturer) which is then used to construct custom queries for Carousell and Reverb
- add reverb searching
- better histogram plotting: doesn't handle outliers too well at the moment (axis gets all funny)
- better filtering (if you cut out products too expensive sometimes makes irrelevant junk come up)
- look at the rest of info returned by carousell (not just results) and see if anything interesting
- use keyword discarding (ex: if 'pedal' in post discard)

goal:
- find undervalued listings
'''

import os, json
import numpy as np
import requests as r
from flask import Flask, request, jsonify

app = Flask(__name__)

print("warning: the matplotlib import was disabled to speed up debugging. uncomment it if you want to generate histograms")

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

    def load_from_json(self, json_object):
        self.title = json_object['listingCard']['belowFold'][0]['stringContent']
        self.price = float(json_object['listingCard']['belowFold'][1]['stringContent'].replace("S", "").replace("$", "").replace(",", ""))
        self.description = json_object['listingCard']['belowFold'][2]['stringContent']
        self.new_or_used = json_object['listingCard']['belowFold'][3]['stringContent']
        self.likes = json_object['listingCard']['likesCount']

class ReverbProduct(Product): 
    def __init__(self):
        super(Product, self).__init__()
        # self.id
        # self.make
        # self.model
        # self.finish
        # self.year
        # self.title
        # self.description
        # self.condition
        # self.price
        # self.buyer_price
        # self.inventory
        # self.has_inventory
        # self.listing_currency
        # self.state

    def load_from_json(self, json_object):
        self.id = json_object['id']
        self.make = json_object['make']
        self.model = json_object['model']
        self.finish = json_object['finish']
        self.year = json_object['year']
        self.title = json_object['title']
        self.description = json_object['description']
        self.condition = json_object['condition']
        self.price = float(json_object['price']['amount'])
        self.buyer_price = json_object['buyer_price']
        self.inventory = json_object['inventory']
        self.has_inventory = json_object['has_inventory']
        self.listing_currency = json_object['listing_currency']
        self.state = json_object['state']
        self.categories = [x['full_name'] for x in json_object['categories']]
        self.links = json_object['_links']

class CarousellSearch():
    '''
    TODO: add documentation + make this fire like Reverb
    '''
    def __init__(self, query=None, number_of_results=22):
        self.query = query
        command_string = "curl -i -s -k -X $'POST' -H $'Host: sg.carousell.com' -H $'Connection: close' -H $'Content-Length: 110' -H $'y-X-Request-ID: QQCiHsizJ2MsUbsT' -H $'Origin: https://sg.carousell.com' -H $'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36' -H $'Content-Type: application/json' -H $'Accept: */*' -H $'Sec-Fetch-Site: same-origin' -H $'Sec-Fetch-Mode: cors' -H $'Referer: https://sg.carousell.com/search/fender%20black%20stratocaster' -H $'Accept-Encoding: gzip, deflate' -H $'Accept-Language: en,en-US;q=0.9,ms;q=0.8' \
            --data-binary $'{\"count\":COUNTPLACEHOLDER,\"countryId\":\"1880251\",\"filters\":[],\"locale\":\"en\",\"prefill\":{},\"query\":\"QUERYPLACEHOLDER\"}' \
            $'https://sg.carousell.com/api-service/filter/search/3.3/products/' --output carouselloutputfile  --compressed"
        
        command_string = command_string.replace("QUERYPLACEHOLDER", query)
        command_string = command_string.replace("COUNTPLACEHOLDER", str(number_of_results))
        print(command_string)
        print(os.system(command_string))

        f = open('carouselloutputfile', 'r')
        dumped_product_list = f.read().split('\n')[-1]
        f.close()

        self.returned_json = json.loads(dumped_product_list)
        self.product_list = self.returned_json['data']['results']

        os.remove('carouselloutputfile')


    def calculate_avg_price(self):
        sum = 0
        count = 0
        prices = []
        for product_json in self.product_list: 
            product = CarousellProduct()
            product.load_from_json(product_json)

            if product.price == 0:
                continue # skip all fake entries

            print(product.title, ": ", product.price)
            sum += product.price
            count += 1
            prices.append(product.price)

        print("=" * 25)
        print("AVERAGE PRICE: ${}".format(sum/count))

        self.generate_histogram(prices, "Price", "Frequency", "Price/Frequency Histogram: {}".format(self.query))


    def generate_histogram(self, data, xlabel, ylabel, title):
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
        
class ReverbSearch():
    '''
    This is the class for a Reverb search. Every search should have its own instance.
    There are several functions to assist with development, and they start with an
    underscore.

    EX: 
    ReverbSearch("fender stratocaster", number_of_results=50, number_of_pages=5, 
        additional_filters={'color': 'sunburst'}, 
        debug_keys={'using_local': True, 'print_links': True, 'print_histogram': False}).calculate_avg_price()
    '''
    def __init__(self, query_string=None, additional_filters={}, search_params={'number_of_results': 22, 'number_of_pages': 3}, 
        debug_keys={'using_local': False, 'print_links': False, 'print_histogram': False}):
        '''
        The constructor is responsible for scraping the list of products for a given query, 
        and initialising appropriate instance variables. 
        '''
        self.debug_keys = debug_keys
        self.search_params = search_params

        self.query = query_string
        self.color = additional_filters['color'] if 'color' in additional_filters.keys() else None

        self.session = r.session()

        payload = additional_filters
        payload['query'] = self.query
        if 'number_of_results' in search_params.keys(): payload['per_page'] = search_params['number_of_results']

        if self.debug_keys['using_local']:
            print("USING LOCAL CACHE")
            self.product_list = eval(open("cached_product_list", "r").read())

            # -- this snippet was used to write the data initially --
            # f = open("cached_product_list", "w")
            # f.write(str(self.product_list))
            # f.close()
        else:
            print("USING LIVE DATA")

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

    def return_filtered_listings(self):
        valid_products = []
        for p_itr in self.product_list:
            p = ReverbProduct()
            p.load_from_json(p_itr)

            validation_checks = {}

            if not self.is_listing_valid(p, custom_validation=validation_checks) or p.price > 5000: continue

            print(p.title, ": ", p.price)
            if self.debug_keys['print_links']: print(p.links['web'])

            valid_products.append(p_itr)

        return valid_products


    def calculate_avg_price(self):
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

            if not self.is_listing_valid(p, custom_validation=validation_checks) or p.price > 5000: continue


            print(p.title, ": ", p.price)
            if self.debug_keys['print_links']: print(p.links['web'])

            prices.append(p.price)
            sum += p.price
            count += 1

        print("=" * 25)
        print("AVERAGE PRICE: ${}".format(sum/count))

        if self.debug_keys['print_histogram'] == True: 
            import matplotlib.pyplot as plt
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
        Generates a histogram of an array of `data`, which we assume is of prices. Shouldn't
        be necessary since using React front-end, but it's here just in case. 
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


## TODO: define this function that takes search parameters and makes reverb + carousell searches
## will be used for Flask -- when React sends the request, so it should return the appropriate
## data that Flask requires/wants
def search():
    pass

'''
Example working request:

POST /find_guitar HTTP/1.1
Host: localhost:5000
Content-Type: application/json
Cache-Control: no-cache
Postman-Token: 3d7bd5be-5112-8ca5-4596-3ee645e9f715

{
    "query_string": "fender stratocaster",
    "additional_filters": {"color": "sunburst"},
    "search_params": {"number_of_results": 22, "number_of_pages": 3},
    "debug_keys": {"using_local": true, "print_links": true, "print_histogram": false}
}
'''


@app.route('/find_guitar', methods=['POST'])
def generate_text():
    request_type = request.content_type
    if request_type == 'application/json':
        req_json = request.get_json()
    elif 'multipart/form-data' in request_type:
        req_json = request.form.to_dict()
    else:
        # WORKING
        return_data = {'id': set_id, 'status': 'error', 'message': 'request content type incorrect', "request_type": request_type}
        log_request(return_data, set_id)
        return jsonify(return_data)

    return_data = {}
    return_data["request_json"] = req_json
    
    # PERFORM THE SEARCH
    reverb_search = ReverbSearch(req_json["query_string"], additional_filters=req_json["additional_filters"], 
        search_params=req_json["search_params"], debug_keys=req_json["debug_keys"])
    # reverb_search = ReverbSearch(req_json["query_string"], number_of_results=50, number_of_pages=3, 
    #     additional_filters={'color': 'sunburst'}, 
    #     debug_keys={'using_local': True, 'print_links': True, 'print_histogram': False})

    data = {}
    data["filtered_listings"] = reverb_search.return_filtered_listings()

    return_data["data"] = data
    return_data["status"] = "success"

    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

# ReverbSearch("fender stratocaster", number_of_results=50, number_of_pages=5, 
    # additional_filters={'color': 'sunburst'}, 
    # debug_keys={'using_local': True, 'print_links': True, 'print_histogram': False}).calculate_avg_price()

# CarousellSearch("fender black stratocaster", number_of_results=50).calculate_avg_price()