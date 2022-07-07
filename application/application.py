#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import *
from flask import request
from flask_sslify import SSLify

# import library and util
from library.functions import *
from util.get_logs import *

# stripe
import stripe
stripe.api_key = STRIPE_SECRET

application = Flask(__name__)
#sslify = SSLify(application)
application.secret_key = 'ENTER SECRET KEY HERE'
application.debug = True
application.version = "1.0.0"

error_dict = {'error': 'Oh-no, something went wrong.'}

UPLOAD_FOLDER = os.path.join(application.root_path, '/tmp/')
SAVE_FOLDER = os.path.join(application.root_path, '/tmp/')
ALLOWED_EXTENSIONS = set(['xml'])

CLIENT = connect_to_mongodb(MONGODB_USERNAME, MONGODB_PASSWORD)

# define databases
DATABASE = CLIENT.test
DB = DATABASE['stocks']
SU = DATABASE['stripe']

# config for application
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
application.config['SAVE_FOLDER'] = SAVE_FOLDER

@application.route('/charge/<portfolio_id>', methods=['POST'])
def stripe_charge(portfolio_id):
  # define price (in cents)
  amount = 995

  # define token and email
  token = request.form['stripeToken']
  email = request.form['card-email']

  if (find_email_in_database(email, SU) == None):
    try:
      user = add_email_to_database(email, SU)

      # update session with upgraded unlocked
      session['upgraded'] = {"email": email, "created": user['created'][0].strftime('%d, %b %Y'), "expire": user['expire'][0].strftime('%d, %b %Y')}

      flash("Thank you! But upgraded features are not ready yet (don't worry we did not charge your card!). Enjoy an increased stock limit for free anyway!")
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))
    
    except stripe.error.CardError as e:
      body = e.json_body
        err  = body.get('error', {})

      flash("%s" % err.get('message'))
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    except stripe.error.StripeError as e:

      flash("An error occured (Stripe): %s" % e)
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    except Exception as e:

      flash("An error occured: %s" % e)
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))
  else:
    flash("This email is already used.")
    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

@application.route('/get_logs/<secret_key>', methods=['GET', 'POST'])
def get_logs_route(secret_key):
  ''''''
  logs_path = 'logs'
  filename = 'logs.zip'

  if (secret_key != application.secret_key):
    abort(404)

  else:
    if (get_logs(logs_path, filename, SAVE_FOLDER) == True):
      return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)

    else:
      return redirect(url_for('index'))

@application.route('/', methods=['GET', 'POST'])
def index(title="BSc Project by Michael Sjoeberg"):
  '''Return index page, or redirect to uploaded file page.'''

  # check session
  if (session.get('portfolio_id') != None):
    portfolio_id = session.get('portfolio_id')

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id, version=application.version))

  # handle form submissions
  if request.method == 'POST':

    # no file
    if ('file' not in request.files):
      flash('No file selected.')

      return redirect(request.url)
    
    # define file
    file = request.files['file']
    
    # no filename
    if (file.filename == ''):
      flash('No file selected.')

      return redirect(request.url)

    # there is a file and filename is allowed
    if (file and allowed_file(file.filename, ALLOWED_EXTENSIONS)):
      config_name = file.filename[:-4]
      filename = str(uuid.uuid4()) + '.xml'
      file.save(os.path.join(UPLOAD_FOLDER, filename))
      
      return redirect(url_for('uploaded_file', filename=filename, config_name=config_name))

    else:
      flash('Can\'t upload this file, please select an XML-file that was created using this tool.')

      return redirect(request.url)

  return render_template('index.html', title=title, version=application.version)

@application.errorhandler(404)
def page_not_found(error, title="Page not found"):
  '''Return error page.'''

  return render_template('404.html', title=title), 404

@application.route('/end_session/<portfolio_id>', methods=['GET', 'POST'])
def end_session(portfolio_id):
  '''Clear session, delete portfolio file, delete document 
     for portfolio in database, and redirect to index page.'''

  add_to_log(portfolio_id, "end session")

  session.clear()
  delete_portfolio(portfolio_id, DB, SAVE_FOLDER)

  return redirect(url_for('index'))

@application.route('/create_new/<content>')
def create_new(content):
  '''Create new portfolio, start session, and redirect 
     to manage portfolio page.'''

  # check session
  if (session.get('portfolio_id') != None):
    portfolio_id = session.get('portfolio_id')

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  # create new portfolio
  portfolio_id = create_new_portfolio(content, DB)

  if (portfolio_id != False):
    session['portfolio_id'] = portfolio_id
    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  else:
    abort(404)

@application.route('/uploaded/<filename>/<config_name>')
def uploaded_file(filename, config_name):
  '''Read uploaded file, start session, and redirect 
     to manage portfolio page.'''

  # check session
  if (session.get('portfolio_id') != None):
    portfolio_id = session.get('portfolio_id')

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  # read from file
  portfolio_id = read_from_file(filename, config_name, DB, UPLOAD_FOLDER)

  if (portfolio_id != False):
    session['portfolio_id'] = portfolio_id

    # update portfolio to validate content
    update_portfolio_in_database(portfolio_id, DB)

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  else:
    flash(error_dict['error'])

    return redirect(url_for('index'))

@application.route('/update/<portfolio_id>')
def update_portfolio(portfolio_id):
  '''Update data in document for portfolio, and 
     redirect to manage portfolio or error page.'''

  try:
    updated = update_portfolio_in_database(portfolio_id, DB)

    # update data in document and redirect to manage portfolio page
    if (updated == True):
      add_to_log(portfolio_id, "update portfolio successful")

      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    elif (updated == -1):
      add_to_log(portfolio_id, "update portfolio no stocks")

      flash('You have not added any stocks.')

      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    # otherwise
    else:
      add_to_log(portfolio_id, "update portfolio error")

      flash('Something went wrong, try again later!')

      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  except Exception as e:
    if (application.debug):
      flash(error_dict['error'] + ' Error: ' + str(e))
    else:
      flash(error_dict['error'])

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

@application.route('/save/<portfolio_id>', methods=['GET', 'POST'])
def save_portfolio(portfolio_id):
  '''Save document in portfolio as XML-file and return 
     file as attachment.'''

  filename = save_portfolio_to_file(portfolio_id, DB, SAVE_FOLDER)

  if (filename != False):
    add_to_log(portfolio_id, "save portfolio successful")

    return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)
  
  else:
    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

@application.route('/export/<portfolio_id>/<format>', methods=['GET', 'POST'])
def export_portfolio(portfolio_id, format):
  '''Export portfolio as format and return 
     file as attachment.'''

  if (format == 'CSV'):
    filename = export_portfolio_to_csv(portfolio_id, DB, SAVE_FOLDER)

    if (filename != False):
      add_to_log(portfolio_id, "export portfolio to CSV")

      return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)
    else:
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  elif (format == 'XLSX'):
    filename = export_portfolio_to_xlsx(portfolio_id, DB, SAVE_FOLDER)

    if (filename != False):
      add_to_log(portfolio_id, "export portfolio to XLSX")

      return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)
    else:
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  else:
    flash('Export is currently not working.')
    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

@application.route('/select_currency/<portfolio_id>/<base_currency>')
def select_currency(portfolio_id, base_currency):
  '''Select currency for a portfolio.'''

  if (base_currency == 'USD' or base_currency == 'GBP' or base_currency == 'EUR'):

    # set new currency
    if (select_base_currency_in_portfolio(portfolio_id, base_currency, DB) == True):
      add_to_log(portfolio_id, "set base currency to " + base_currency)

      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    # otherwise flash and return
    else:
      flash('Could not change currency, try again later!')
      return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  else:
    abort(404)

@application.route('/toggle_mode/<portfolio_id>/<mode>')
def toggle_mode(portfolio_id, mode):
  '''Toggle mode for a portfolio.'''

  # abort if session is different from portfolio id
  if (session.get('portfolio_id') != portfolio_id):
    abort(404)

  # set portfolio config to selected mode
  if (update_mode_in_portfolio(portfolio_id, mode, DB) == True):

    add_to_log(portfolio_id, "toggle mode to " + mode)

    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

  else:
    return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

@application.route('/portfolio/<portfolio_id>', methods=['GET', 'POST'])
def manage_portfolio(portfolio_id): 
  '''Get document for portfolio in database, calculate 
     values, and return manage portfolio page.'''

  # abort if session is different from portfolio id
  if (session.get('portfolio_id') != portfolio_id):
    abort(404)

  if (session.get('upgraded')):
    upgraded = True
    user = session.get('upgraded')
  else:
    upgraded = False
    user = None

  # get exchange rates
  rates = get_exchange_rates()

  # reset template defaults
  portfolio_value, portfolio_cost, portfolio_profit, portfolio_change = 0, 0, 0, 0

  # get portfolio
  portfolio = get_portfolio(portfolio_id, DB)

  name = str(portfolio['config'][0]['name'])
  content = str(portfolio['config'][0]['content'])
  base_currency = str(portfolio['config'][0]['base_currency']).upper()
  mode = str(portfolio['config'][0]['mode'])
  date = str(portfolio['config'][0]['date'])

  # set exchange rate
  if (base_currency == 'EUR'):
    exchange_rate = float(rates['USD_EUR'])
    currency_symbol = unichr(8364)
  elif (base_currency == 'GBP'):
    exchange_rate = float(rates['USD_GBP'])
    currency_symbol = unichr(163)
  else:
    exchange_rate = 1
    currency_symbol = '$'

  # stocks
  if (content == "stocks"):
    # handle form submissions to add and remove a stock
    if (request.method == 'POST'):
      # unlock upgraded features
      if (request.form['formType'] == "unlock_portfolio"):
        email = request.form['formUnlockEmail']

        user = find_email_in_database(email, SU)

        if (user != None):
          # update session with upgraded unlocked
          session['upgraded'] = {"email": email, "created": user['created'][0].strftime('%d, %b %Y'), "expire": user['expire'][0].strftime('%d, %b %Y')}

          flash("Upgraded features unlocked (expire %s)" % user['expire'][0].strftime('%d, %b %Y'))
          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

        else:
          flash("No upgraded features for this email, or it has expired.")
          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))
      
      # add ticker to portfolio
      if (request.form['formType'] == "add_ticker"):
        ticker = request.form['formAddTicker'].upper()
        shares = request.form['formAddShares']
        cost = request.form['formAddCost']
        cost_currency = request.form['formSelectCurrency'].upper()

        if (add_ticker_to_portfolio(portfolio_id, ticker, shares, cost, cost_currency, DB, upgraded) == True):
          add_to_log(portfolio_id, "add ticker " + ticker)

          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))
        elif (add_ticker_to_portfolio(portfolio_id, ticker, shares, cost, cost_currency, DB, upgraded) == -1):
          flash("You have reach the maximum number of stocks (free limit), upgrade to premium to increase the limit.")

          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

        elif (add_ticker_to_portfolio(portfolio_id, ticker, shares, cost, cost_currency, DB, upgraded) == -2):
          flash("You have reach the maximum number of stocks (upgraded limit).")

          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

      # remove ticker from portfolio
      if (request.form['formType'] == "remove_ticker"):
        ticker = request.form['formRemoveTicker'].upper()

        if (remove_ticker_from_portfolio(portfolio_id, ticker, DB) == True):
          add_to_log(portfolio_id, "remove ticker " + ticker)

          return redirect(url_for('manage_portfolio', portfolio_id=portfolio_id))

    try:
      stock_lst = []

      if (portfolio['stocks'] != [{}] ):

        # calculate and define portfolio total value and cost
        for stock in portfolio['stocks']:
          portfolio_value = portfolio_value + (float(stock['price'] * exchange_rate) * float(stock['shares']))
          portfolio_cost = portfolio_cost + float(stock['cost'])

        # calculate portfolio profit
        portfolio_profit = (portfolio_value - portfolio_cost) * exchange_rate

        # calculate portfolio change
        if (portfolio_cost != 0):
          portfolio_change = ((portfolio_value / portfolio_cost) - 1) * 100

        for stock in portfolio['stocks']:

          # reset stock defaults
          allocation = 0
          change = 0

          # define stock data
          ticker = str(stock['ticker'])
          name = str(stock['name'])
          sector = str(stock['sector'])

          # calculation guards
          if (stock['price'] != None):
            price = float(stock['price']) * exchange_rate
          else:
            price = 0
          if (stock['marketcap'] != None):
            marketcap = int(stock['marketcap']) * exchange_rate
          else:
            marketcap = 0
          if (stock['day_change'] != None):
            day_change = float(stock['day_change']) * 100
          else:
            day_change = 0
          if (stock['ytd_change'] != None):
            ytd_change = float(stock['ytd_change']) * 100
          else:
            ytd_change = 0
          # end calculation guards
          
          shares = float(stock['shares'])
          cost_currency = str(stock['cost_currency'])
          value = float(price * shares)

          # define company data
          industry = str(stock['industry'])
          website = str(stock['website'])
          description = str(stock['description'])
          ceo = str(stock['ceo'])

          if (cost_currency == 'EUR'):
            cost = (float(stock['cost']) / float(rates['USD_EUR'])) * exchange_rate

          elif (cost_currency == 'GBP'):
            cost = (float(stock['cost']) / float(rates['USD_GBP'])) * exchange_rate

          else:
            cost = float(stock['cost']) * exchange_rate

          # get news for stocks in portfolio
          news = get_news(ticker)

          # define stock allocation
          if (portfolio_value != 0):
            allocation = float((value / portfolio_value) * 100)

          # define stock change
          if (cost != 0):
            change = ((value / cost) - 1) * 100

          # append stock data to list
          stock_lst.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "price": price,
            "marketcap": marketcap,
            "day_change": day_change,
            "ytd_change": ytd_change,
            "shares": shares,
            "cost": cost,
            "value": value,
            "allocation": allocation,
            "change": change,
            "industry": industry,
            "website": website,
            "description": description,
            "ceo": ceo, 
            "news": news
          })

      return (render_template('portfolio.html', 
        title="Manage portfolio: " + portfolio_id,
        version=application.version,
        portfolio_id=portfolio_id,
        upgraded=upgraded,
        user=user,
        stock_lst=stock_lst,
        stock_lst_size=len(stock_lst),
        portfolio_value=portfolio_value,
        portfolio_profit=portfolio_profit,
        portfolio_change=portfolio_change,
        content=content,
        mode=mode,
        date=date,
        currency=base_currency,
        currency_symbol=currency_symbol,
        usd_eur=rates['USD_EUR'],
        usd_gbp=rates['USD_GBP'],
        key=STRIPE_PUBLISHABLE))

    except Exception as e:
      if (application.debug):
        flash(error_dict['error'] + ' Error: ' + str(e))
      else:
        flash(error_dict['error'])

      return redirect(url_for('end_session', portfolio_id=portfolio_id))

if __name__ == '__main__':
  application.run(threaded = True)
