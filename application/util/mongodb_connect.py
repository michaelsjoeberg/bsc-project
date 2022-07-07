# --------------------------------------------------------
# MongoDB Atlas Credentials
#   
# Use 'import mongodb_connect' to use hosted database, 
# keep this file private.
# --------------------------------------------------------
import pymongo

def mongodb_connect():
  '''Function to connect to MongoDB Atlas hosted database.'''
    
  # mongodb atlas cluster credentials
  USERNAME = "ENTER USERNAME HERE"
  PASSWORD = "ENTER PASSWORD HERE"

  try:
    return pymongo.MongoClient("mongodb+srv://" + USERNAME + ":" + PASSWORD + "@bsc-project-cluster-1-54tnn.mongodb.net/test?retryWrites=true")
    
  except:
    return False
