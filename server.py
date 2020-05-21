'''
File containing example Flask server. This can be used as a starting point
for a web frontend for the search classes.
'''

from flask import Flask, request, jsonify
from fendir import ReverbSearch

app = Flask(__name__)

@app.route('/find_guitar', methods=['POST'])
def generate_text():
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

