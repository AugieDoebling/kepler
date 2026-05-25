from pymongo import MongoClient
import certifi
from bson.objectid import ObjectId

# TODO move to config
client = MongoClient(uri, tlsCAFile=certifi.where())

def get_msg_scores(word):
   database = client.get_database("kepler")
   word_scores_collection = database.get_collection("word_scores")

   query = {"word": word}
   found_words = word_scores_collection.find(query)

   return [(word["msg_id"], word["score"]) for word in found_words]

def get_messages(message_ids: list[str]):
   database = client.get_database("kepler")
   messages_collection = database.get_collection("messages")

   return [messages_collection.find_one({"_id": ObjectId(msg_id)})["message"] for msg_id in message_ids]

