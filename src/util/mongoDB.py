import pymongo
import random, string
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
#print(sys.path)
from .apiKey import getApiKey

class ControlMongo:
    def __init__(self, username, password, dbName, collName):
        try:
            conn = pymongo.MongoClient(host=getApiKey("MONGODB_URL"), port=int(getApiKey("MONGODB_PORT")), username=username, password=password)
            # print(int(getApiKey("MONGODB_PORT")))
            db = conn.get_database(dbName)
            self.coll = db.get_collection(collName)
        except Exception as e:
            raise Exception(f"DB Connection ERROR: {e}")


    def selectDB(self, queryDict={}):
        if queryDict == {}:
            return [result for result in self.coll.find()]
        else:
            return [result for result in self.coll.find(queryDict)]

    def insertDB(self, insertDict):
        try:
            self.coll.insert_one(insertDict)
        except Exception as e: 
            raise Exception(f"DB insert ERROR : {e}")
        
        return True

    def deleteDB(self, queryDict, isMulti=False):
        try:
            if isMulti:
                self.coll.delete_many(queryDict)
            else:
                self.coll.delete_one(queryDict)
        except Exception as e: 
            return False, f"DB remove ERROR : {e}"

        return True, ""

    def updateDB(self, queryDict, modifyDict, isMulti=False, isUpsert=False):
        try:
            if isMulti:
                self.coll.update_one(queryDict, {"$set":modifyDict}, upsert=isUpsert)
            else:
                self.coll.update_many(queryDict, {"$set":modifyDict}, upsert=isUpsert)
        except Exception as e: 
            # raise Exception(f"DB update ERROR : {e}")
            return False

        return True
