import sys
import pymongo

from datetime import datetime
from datetime import timedelta

# import from dir above
sys.path.append("..")

from library.functions import connect_to_mongodb
from globals_private import *

CLIENT = connect_to_mongodb(MONGODB_USERNAME, MONGODB_PASSWORD)

# define databases
DATABASE = CLIENT.test
SU = DATABASE['stripe']

all_documents = SU.find({})
now = datetime.now()

def list_all(all_documents, now):
  '''Print all user documents.'''
  print(":::: All")
  for document in all_documents.rewind():
    print (str(document['expire'][0]) + " : " + str(document['_id']))

  print("")

def list_today(all_documents, now):
  '''Print today user documents.'''
  print(":::: Today")
  for document in all_documents.rewind():
    if ((document['expire'][0].day == now.day)):
      print (str(document['expire'][0]) + " : " + str(document['_id']))

  print("")

def list_expired(all_documents, now):
  '''Print expired user documents.'''
  print(":::: Expired")
  for document in all_documents.rewind():
    if (document['expire'][0] < now):
      print (str(document['expire'][0]) + " : " + str(document['_id']))

  print("")

def purge_expired(all_documents, now):
  '''Purge expired user documents.'''
  purge_counter = 0
  for document in all_documents.rewind():
    if (document['expire'][0] < now):
      SU.delete_one({"_id": document['_id']})
      purge_counter = purge_counter + 1

  print(":::: Purged %s documents" % purge_counter)
  print("")

list_all(all_documents, now)
#list_today(all_documents, now)
list_expired(all_documents, now)
purge_expired(all_documents, now)

