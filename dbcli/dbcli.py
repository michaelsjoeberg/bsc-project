#!/usr/bin/python

import sys, pymongo

# hosted database
# from mongodb_connect import *
# client = mongodb_connect()

CLIENT = pymongo.MongoClient("mongodb://localhost:27017/", connect=False)

database = CLIENT.test
DB = database['stocks']

def main():
  '''Print active portfolios in database.'''
  active_portfolios = DB.find()

  print('\nCurrent active portfolios in database:')
  # print portfolio id for each active portfolio in database
  for portfolio in active_portfolios:
    #print (str(portfolio['_id']))
    print (portfolio)

def drop_all():
  '''Drop all active portfolios in database.'''
  DB.remove({})


if __name__ == "__main__":
  try:
    arg = sys.argv[1]

    if (arg == "drop"):
      print('You are about to drop all active portfolios, continue? [Y/n]')
      
      user_input = raw_input()
      if (user_input == "Y"):
        drop_all()

  except Exception as err:
    #print(err)
    main()
