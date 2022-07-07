#!/usr/bin/python

import os
import uuid
import sys
import pymongo
import requests
import xlsxwriter
import dns

from datetime import datetime
from datetime import timedelta
from lxml import etree

def find_email_in_database(email, SU):
  '''Find and return email in super user database.'''

  return SU.find_one({"_id": email})

def add_email_to_database(new_email, SU):
  '''Add an email to the super user database.'''

  # create new document for email
  email = {"_id": new_email}
  email_id = SU.insert_one(email).inserted_id

  # define creation and expire date
  created = datetime.now()
  expire = datetime.now() + timedelta(30)

  try:
    SU.update_one(
      {"_id": email_id},
      {"$push": { 
        "created": created,
        "expire": expire
        }
      }
    )

    return find_email_in_database(new_email, SU)

  except:
    return False

def create_new_portfolio(content, DB):
  ''''Create a new document for portfolio in database.'''

  filename = new_filename()

  # create new document for portfolio in database
  portfolio = {"_id": filename[:-4]}
  portfolio_id = DB.insert_one(portfolio).inserted_id

  try:
    if (content == "stocks"):
      # add config
      DB.update_one(
        {"_id": portfolio_id},
        {"$push": {"config": {"name": 'Untitled Portfolio', "content": 'stocks', 'base_currency': 'USD', "mode": 'normal', 'date': str(datetime.now())}}})

      # add empty portfolio
      DB.update_one(
        {"_id": portfolio_id},
        {"$push": {"stocks": {} }})

    return portfolio_id

  except:
    return False

def read_from_file(filename, config_name, DB, UPLOAD_FOLDER):
  '''Read data from file, create document for portfolio in database, and return portfolio id.'''

  # create new document for portfolio in database
  portfolio = {"_id": filename[:-4]}
  portfolio_id = DB.insert_one(portfolio).inserted_id
    
  try:
    # read from file
    with open(os.path.join(UPLOAD_FOLDER, filename), 'r') as file:
      root = etree.parse(file)

      # iterate config
      for config in root.xpath('/portfolio/config'):

        # define config
        config_content = str(config.find('content').text)
        config_base_currency = str(config.find('base_currency').text)
        config_mode = str(config.find('mode').text)
        config_date = str(config.find('date').text)

        # update config to document for portfolio in database
        DB.update_one(
          {"_id": portfolio_id},
          {"$push": {"config": 
            {
              "name": config_name, 
              "content": config_content, 
              "base_currency": config_base_currency, 
              "mode": config_mode, 
              "date": config_date
            }
          }})

      if (config_content == "stocks"):

        # iterate each stock
        for stock in root.xpath('/portfolio/stock'):

          # define stock values
          ticker = str(stock.find('symbol').text)
          shares = str(stock.find('shares').text)
          cost = str(stock.find('cost').text)
          cost_currency = str(stock.find('cost_currency').text)

          DB.update_one(
            {"_id": portfolio_id},
            {"$push": {"stocks": 
              {
                "ticker": ticker,
                "shares": shares, 
                "cost": cost, 
                "cost_currency": cost_currency
              }
            }})

    file.close()

    # remove uploaded file from server
    os.remove(os.path.join(UPLOAD_FOLDER, filename))

    return portfolio_id

  except:
    return False

def update_portfolio_in_database(portfolio_id, DB):
  '''Update data in document for portfolio.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  # string for batch request
  stock_string = ''

  # dict with portfolio data
  portfolio_data = {}

  if (portfolio['stocks'] != [{}] ):
    for stock in portfolio['stocks']:
      
      # define stock values for portfolio
      ticker = str(stock['ticker']).upper()
      shares = float(stock['shares'])
      cost = float(stock['cost'])
      cost_currency = str(stock['cost_currency'])

      # append ticker to string
      stock_string = stock_string + str(ticker) + ','

      # add portfolio data to dict
      portfolio_data.update({ticker: {'shares': shares, 'cost': cost, 'cost_currency': cost_currency}})

    try:
      request = requests.get('https://api.iextrading.com/1.0/stock/market/batch?symbols=' + stock_string + '&types=quote,company')
      response = request.json()

      stock_lst = []

      for stock in response:
        # get stock data from API response
        ticker = response[stock]['quote']['symbol']
        name = response[stock]['quote']['companyName']
        price = response[stock]['quote']['latestPrice']
        marketcap = response[stock]['quote']['marketCap']
        day_change = response[stock]['quote']['changePercent']
        ytd_change = response[stock]['quote']['ytdChange']

        # get company data from API response
        sector = response[stock]['company']['sector']
        industry = response[stock]['company']['industry']
        description = response[stock]['company']['description']
        ceo = response[stock]['company']['CEO']
        website = response[stock]['company']['website']

        # import from portfolio data
        shares = portfolio_data[ticker]['shares']
        cost = portfolio_data[ticker]['cost']
        cost_currency = portfolio_data[ticker]['cost_currency']

        # create stock object
        stock = {
          "ticker": ticker, 
          "name": name,
          "price": price,
          "marketcap": marketcap,
          "day_change": day_change,
          "ytd_change": ytd_change, 
          "shares": shares, 
          "cost": cost, 
          "cost_currency": cost_currency,
          "sector": sector,
          "industry": industry,
          "description": description,
          "ceo": ceo,
          "website": website
        }
        
        stock_lst.append(stock)

      # update list for stocks to document for portfolio in database
      DB.update_one(
        {"_id": portfolio_id},
        {"$set": {"stocks": stock_lst}})

      return True

    except:
      return False

  else:
    return -1

def save_portfolio_to_file(portfolio_id, DB, SAVE_FOLDER):
  '''Save data in document for portfolio to file.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  name = str(portfolio['config'][0]['name'])
  content = str(portfolio['config'][0]['content'])
  base_currency = str(portfolio['config'][0]['base_currency']).upper()
  mode = str(portfolio['config'][0]['mode'])
  date = str(portfolio['config'][0]['date'])

  if (content == "stocks"):

    try:
      if (portfolio['stocks'] == [{}] ):
        return False

      else:
        # define filename
        filename = name + '.xml'

        # write to file (created if not already exists)
        with open(os.path.join(SAVE_FOLDER, filename), 'w+') as file:

          # write XML for header
          file.write("""<?xml version="1.0" encoding="UTF-8"?>\n""")
          file.write("""<portfolio>\n""")

          # write XML for config
          file.write("""\t<config>\n""")
          file.write("""\t\t<name>"""       + name        + """</name>\n""")
          file.write("""\t\t<content>"""      + content       + """</content>\n""")
          file.write("""\t\t<base_currency>"""    + base_currency   + """</base_currency>\n""")
          file.write("""\t\t<mode>"""       + mode        + """</mode>\n""")
          file.write("""\t\t<date>"""       + date        + """</date>\n""")
          file.write("""\t</config>\n""")

          # write XML for stocks
          for stock in portfolio['stocks']:
            ticker = str(stock['ticker'])
            shares = str(stock['shares'])
            cost = str(stock['cost'])
            cost_currency = str(stock['cost_currency'])

            file.write("""\t<stock>\n""")
            file.write("""\t\t<symbol>"""       + ticker        + """</symbol>\n""")
            file.write("""\t\t<shares>"""       + shares      + """</shares>\n""")
            file.write("""\t\t<cost>"""       + cost        + """</cost>\n""")
            file.write("""\t\t<cost_currency>"""    + cost_currency   + """</cost_currency>\n""")
            file.write("""\t</stock>\n""")

          file.write("""</portfolio>""")

        file.close()

        return filename

    except:
      flash('Something went wrong, couldn\'t save to file.')
      return False

def delete_portfolio(portfolio_id, DB, SAVE_FOLDER):
  '''Delete a saved portfolio file on server.'''
  
  filename = portfolio_id + '.xml'

  try:
    DB.remove({"_id": portfolio_id})
    os.remove(os.path.join(SAVE_FOLDER, filename))
    
    return True

  except:
    return False

def add_ticker_to_portfolio(portfolio_id, ticker, shares, cost, cost_currency, DB, upgraded):
  '''Add ticker to document for portfolio.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)
  
  stock_lst = []

  # check if portfolio is not empty and iterate stocks
  if (portfolio['stocks'] != [{}] ):
    for stock in portfolio['stocks']:
      # append ticker to stock list
      stock_lst.append(str(stock['ticker']))

    if (not upgraded and len(stock_lst) >= 20):
      return -1

    elif (len(stock_lst) == 100):
      return -2

  # otherwise remove initial brackets (consider changing this in the future)
  else:
    DB.update_one(
      {"_id": portfolio_id},
      {"$pull": {"stocks": {} }})

  # define default values for tracking only
  if (shares == "" or cost == ""):
    shares = 0
    cost = 0
  
  if (ticker not in stock_lst):
    try:
      request = requests.get('https://api.iextrading.com/1.0/stock/market/batch?symbols=' + ticker + '&types=quote,company')
      response = request.json()

      # get stock data from API response
      ticker = response[ticker]['quote']['symbol']
      name = response[ticker]['quote']['companyName']
      price = response[ticker]['quote']['latestPrice']
      marketcap = response[ticker]['quote']['marketCap']
      day_change = response[ticker]['quote']['changePercent']
      ytd_change = response[ticker]['quote']['ytdChange']

      # get company data from API response
      sector = response[ticker]['company']['sector']
      industry = response[ticker]['company']['industry']
      description = response[ticker]['company']['description']
      ceo = response[ticker]['company']['CEO']
      website = response[ticker]['company']['website']

      # update stock values to document for portfolio in database
      DB.update_one(
        {"_id": portfolio_id},
        {"$push": {"stocks": 
          {
            "ticker": ticker, 
            "name": name,
            "price": price,
            "marketcap": marketcap,
            "day_change": day_change,
            "ytd_change": ytd_change, 
            "shares": shares, 
            "cost": cost, 
            "cost_currency": cost_currency,
            "sector": sector,
            "industry": industry,
            "description": description,
            "ceo": ceo,
            "website": website
          }
        }})

      return True

    except:
      return False

  else:
    return False

def remove_ticker_from_portfolio(portfolio_id, ticker, DB):
  '''Remove ticker from document for portfolio.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  stock_lst = []

  if (portfolio['stocks'] != [{}] ):
    for stock in portfolio['stocks']:

      # append ticker to stock list
      stock_lst.append(str(stock['ticker']))

  # remove if ticker exists
  if (ticker in stock_lst):
    DB.update_one(
      {"_id": portfolio_id},
      {"$pull": {"stocks": {"ticker": ticker}}})

    return True

  else:
    return False

def update_mode_in_portfolio(portfolio_id, mode, DB):
  '''Update config in portfolio, currently only mode.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  current_name = str(portfolio['config'][0]['name'])
  current_content = str(portfolio['config'][0]['content'])
  current_base_currency = str(portfolio['config'][0]['base_currency']).upper()
  current_mode = str(portfolio['config'][0]['mode'])
  current_date = str(portfolio['config'][0]['date'])

  if (mode != current_mode):
    try:
      DB.update_one(
        {"_id": portfolio_id},
        {"$pull": {"config": 
          {
            "name": current_name, 
            "content": current_content, 
            "base_currency": current_base_currency, 
            "mode": current_mode, 
            "date": current_date
          }
        }})

      DB.update_one(
        {"_id": portfolio_id},
        {"$push": {"config": 
          {
            "name": current_name,
            "content": current_content,
            "base_currency": current_base_currency,
            "mode": mode, 
            "date": current_date
          }
        }})

      return True

    except:
      return False
  
  else:
    return False

def export_portfolio_to_csv(portfolio_id, DB, SAVE_FOLDER):
  '''Export data in document for portfolio to csv-file.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  name = str(portfolio['config'][0]['name'])
  content = str(portfolio['config'][0]['content'])

  if (content == "stocks"):

    try:
      if (portfolio['stocks'] == [{}] ):
        return False

      else:
        # define filename
        filename = name + '.csv'

        # write to file (created if not already exists)
        with open(os.path.join(SAVE_FOLDER, filename), 'w+') as file:

          # write header
          file.write("""ticker,name,price,marketcap,day_change,ytd_change,shares,cost,cost_currency,sector,industry,description,ceo,website\n""")

          # write stocks
          for stock in portfolio['stocks']:

            file.write(str(stock['ticker'])     + """,""")
            file.write(str(stock['name'])       + """,""")
            file.write(str(stock['price'])      + """,""")
            file.write(str(stock['marketcap'])    + """,""")
            file.write(str(stock['day_change'])   + """,""")
            file.write(str(stock['ytd_change'])   + """,""")
            file.write(str(stock['shares'])     + """,""")
            file.write(str(stock['cost'])       + """,""")
            file.write(str(stock['cost_currency'])  + """,""")
            file.write(str(stock['sector'])     + """,""")
            file.write(str(stock['industry'])     + """,""")
            file.write(str(stock['description'])  + """,""")
            file.write(str(stock['ceo'])      + """,""")
            file.write(str(stock['website'])    + """\n""")

        file.close()

        return filename

    except:
      flash('Something went wrong, couldn\'t export to CSV.')
      return False

def export_portfolio_to_xlsx(portfolio_id, DB, SAVE_FOLDER):
  '''Export data in document for portfolio to xlsx-file.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  name = str(portfolio['config'][0]['name'])
  content = str(portfolio['config'][0]['content'])

  if (content == "stocks"):

    try:
      if (portfolio['stocks'] == [{}] ):
        return False

      else:
        # define filename
        filename = name + '.xlsx'

        # create a workbook and add a worksheet
        workbook = xlsxwriter.Workbook(os.path.join(SAVE_FOLDER, filename))
        worksheet = workbook.add_worksheet()

        # write header
        worksheet.write('A1', 'ticker')
        worksheet.write('B1', 'name')
        worksheet.write('C1', 'price')
        worksheet.write('D1', 'marketcap')
        worksheet.write('E1', 'ytd_change')
        worksheet.write('F1', 'shares')
        worksheet.write('G1', 'cost')
        worksheet.write('H1', 'cost_currency')
        worksheet.write('I1', 'sector')
        worksheet.write('J1', 'industry')
        worksheet.write('K1', 'description')
        worksheet.write('L1', 'ceo')
        worksheet.write('M1', 'website')

        # starting row for stock data
        row = 2

        # iterate and write stocks
        for stock in portfolio['stocks']:

          worksheet.write('A' + str(row), str(stock['ticker']))
          worksheet.write('B' + str(row), str(stock['name']))
          worksheet.write('C' + str(row), str(stock['price']))
          worksheet.write('D' + str(row), str(stock['marketcap']))
          worksheet.write('E' + str(row), str(stock['ytd_change']))
          worksheet.write('F' + str(row), str(stock['shares']))
          worksheet.write('G' + str(row), str(stock['cost']))
          worksheet.write('H' + str(row), str(stock['cost_currency']))
          worksheet.write('I' + str(row), str(stock['sector']))
          worksheet.write('J' + str(row), str(stock['industry']))
          worksheet.write('K' + str(row), str(stock['description']))
          worksheet.write('L' + str(row), str(stock['ceo']))
          worksheet.write('M' + str(row), str(stock['website']))

          row = row + 1

        workbook.close()

        return filename

    except:
      flash('Something went wrong, couldn\'t export to XLSX.')
      return False

def select_base_currency_in_portfolio(portfolio_id, base_currency, DB):
  '''Update currency in portfolio.'''

  # find document for portfolio in database
  portfolio = get_portfolio(portfolio_id, DB)

  current_name = str(portfolio['config'][0]['name'])
  current_content = str(portfolio['config'][0]['content'])
  current_base_currency = str(portfolio['config'][0]['base_currency']).upper()
  current_mode = str(portfolio['config'][0]['mode'])
  current_date = str(portfolio['config'][0]['date'])

  if (base_currency != current_base_currency):
    try:
      DB.update_one(
        {"_id": portfolio_id},
        {"$pull": {"config": 
          {
            "name": current_name, 
            "content": current_content, 
            "base_currency": current_base_currency, 
            "mode": current_mode, 
            "date": current_date
          }
        }})

      DB.update_one(
        {"_id": portfolio_id},
        {"$push": {"config": 
          {
            "name": current_name, 
            "content": current_content, 
            "base_currency": base_currency, 
            "mode": current_mode, 
            "date": current_date
          }
        }})

      return True

    except:
      return False

  else:
    return False

# ----------------------------------------- #

def allowed_file(filename, ALLOWED_EXTENSIONS):
  '''Check uploaded file against allowed extensions.'''
  
  return '.' in filename and \
      filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def new_filename():
  '''Generate a new unique filename.'''

  return str(uuid.uuid4()) + '.xml'

def get_portfolio(portfolio_id, DB):
  '''Get a portfolio in database.'''

  try:
    return DB.find_one({"_id": portfolio_id})

  except:
    return False

def connect_to_mongodb(USERNAME, PASSWORD):
    '''Function to connect to MongoDB hosted database.'''
    
    try:
        return pymongo.MongoClient("mongodb+srv://" + USERNAME + ":" + PASSWORD + "@modelmode-cluster-1-54tnn.mongodb.net/test?retryWrites=true")
    
    except:
        return False

def get_exchange_rates():
  '''Get exchange rates for different currencies.'''
  USD_EUR = 'USD_EUR'
  USD_GBP = 'USD_GBP'

  # request exchange rate using external api
  request = requests.get('http://free.currencyconverterapi.com/api/v5/convert?q=' + USD_EUR + ',' + USD_GBP + '&compact=ultra')
  response = request.json()

  return {USD_EUR: response[USD_EUR], USD_GBP: response[USD_GBP]}

def get_news(ticker):
  '''Get news for a ticker.'''

  try:
    # request exchange rate using external api
    request = requests.get('https://api.iextrading.com/1.0/stock/' + ticker + '/news')
    response = request.json()

    news_object = {
      'headline': response[0]['headline'],
      'summary': response[0]['summary'].strip(),
      'source': response[0]['source'],
      'url': response[0]['url'],
      'date': response[0]['datetime'][:10]
    }

    return news_object

  except:
    return False

def add_to_log(portfolio_id, entry):
  '''Add a log entry for a portfolio id.'''

  try:
    # replace 'main.txt' with current month-year
    with open('logs/' + str(portfolio_id) + '.txt', 'a') as file:
      file.write(str(datetime.now()) + "," + str(portfolio_id) + "," + entry + "\n")

    file.close()

    return True

  except Exception as e:
    
    return False
