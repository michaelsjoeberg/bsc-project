# --------------------------------------------------------
# Get all available stocks
#   
# Script to request all available stocks from IEX Group
# API, creates an HTML-file.
# --------------------------------------------------------
import requests
import json

request = requests.get('https://api.iextrading.com/1.0/ref-data/symbols')
response = request.json()

with open('../templates/stocks.html', 'w+') as f:
  # write hidden option
  f.write('<option style="display: none" id="remove">Select stock</option>')

  for item in response:
    # define stock
    symbol = item['symbol']
    name = item['name']

    # write to file
    f.write('<option data-subtext="' + str(name) + '" value="' + str(symbol) + '">' + str(symbol) + '</option>')

f.close()