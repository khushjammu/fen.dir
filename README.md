<h1 align="center"><b>Fen.Dir</b></h1>

Fen.Dir is a utility for finding undervalued guitar listings on Carousell and Reverb! 

## Features
- [x] Scrape guitar listings from Carousell and Reverb
- [x] Built-in listing validation and filtering
- [x] Price Histogram Display
- [x] Identify undervalued (relative to average price) listings

## Requirements
- Python 3
- Libraries specified in `requirements.txt`

## Usage

Place `fendir.py` in the same directory as your project files. 

### Importing 

```python
from fendir import ReverbSearch, CarousellSearch
```

#### Searching Reverb

Reverb is an excellent marketplace, with high-quality listings and no keyword stuffing. You can, therefore, expect high-quality results from the Reverb search. 

```python
ReverbSearch("fender stratocaster HSS floyd rose", search_params={'number_of_results':50, 'number_of_pages':3}, 
    additional_filters={'neck_material': ['maple'], 'color': 'sunburst'}).find_undervalued_listings()
```


### Searching Carousell

Carousell has far fewer features and more spammy listings (keyword stuffing) compared to Reverb. The search results are therefore not as good as they good be. 

```python
CarousellSearch("fender stratocaster", additional_filters={"brand": "fender", "model": "stratocaster", "color": "black"}).find_undervalued_listings()
```

## Flask Server

It is certainly possible to create a web front-end for our search classes. In `server.py`, you can find an example starting point for how you might go about that. 

## Documentation

We make use of extensive documentation within our codebase, explaining the purpose of each function and class, as well as for in-line clarification. 
