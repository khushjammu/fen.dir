'''
todos:
- add ability get more than 50 items (currently maxes out then)
- add better searching logic: specify search object (includes color, make, manufacturer) which is then used to construct custom queries for Carousell and Reverb
- add reverb searching
- better histogram plotting: doesn't handle outliers too well at the moment (axis gets all funny)
- better filtering (if you cut out products too expensive sometimes makes irrelevant junk come up)
- look at the rest of info returned by carousell (not just results) and see if anything interesting
- use keyword discarding (ex: if 'pedal' in post discard)
'''

import os, json
import matplotlib.pyplot as plt
import numpy as np
import requests as r

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

class CarousellSearch():
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
    def __init__(self, query=None, number_of_results=22, color="black"):
        self.query = query
        self.color = color

        self.session = r.session()
        
        payload={'query': 'Fender Stratocaster'}
        
        response = self.session.get('https://api.reverb.com/api/listings/all', headers={'Accept-Version': "3.0"}, params=payload).text

        returned_json = json.loads(response)

        self.product_list = returned_json['listings']

        # count = 0
        # while 'next' in returned_json['_links'] and count < 10:
        #     response = self.session.get(returned_json['_links']['next']['href'], headers={'Accept-Version': "3.0"}).text
        #     try:
        #         returned_json = json.loads(response)
        #     except TypeError as e:
        #         print(response, response.text)
        #         raise e
        #     self.product_list.extend(returned_json['listings'])
        #     print(returned_json['_links'])
        #     count += 1


    def calculate_avg_price(self):
        sum = 0
        count = 0
        prices = []

        for p_itr in self.product_list:
            # print(p_itr)
            p = ReverbProduct()
            p.load_from_json(p_itr)
            # print(p.categories)
            # exit()/

            if not self.is_listing_valid(p):
            if (self.color not in p.description and self.color not in p.title and self.color not in p.make and self.color not in p.finish):
                continue

            print(p.title, ": ", p.price)
            prices.append(p.price)
            sum += p.price
            count += 1

        print("=" * 25)
        print("AVERAGE PRICE: ${}".format(sum/count))

    def is_listing_valid(self, product_object):
        if "Electric Guitar" not in 
        
        




        # sum = 0
        # count = 0
        # prices = []
        # for product_json in self.product_list: 
            # product = CarousellProduct()
            # product.load_from_json(product_json)

            # if product.price == 0:
                # continue # skip all fake entries

            # print(product.title, ": ", product.price)
            # sum += product.price
            # count += 1
            # prices.append(product.price)

        # print("=" * 25)
        # print("AVERAGE PRICE: ${}".format(sum/count))

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

ReverbSearch("fender black stratocaster", number_of_results=50).calculate_avg_price()
# CarousellSearch("fender black stratocaster", number_of_results=50).calculate_avg_price()