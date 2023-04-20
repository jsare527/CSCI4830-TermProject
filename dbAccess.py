from pymongo import MongoClient
from bson import ObjectId
from userAuth import User
from datetime import datetime
import uuid

DB_PASSWORD = "cmJG8icwu25gFDRI"
DB_ACCESS = f"mongodb+srv://jsare527:{DB_PASSWORD}@termproject.8hcqb9v.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(DB_ACCESS)

db = client.get_database("TermProject")
users = db.get_collection("Users")
rooms = db.get_collection("Rooms")
roomMembers = db.get_collection("RoomMembers")


def saveUser(email, username, password):
    users.insert_one({
        '_id': username,
        'email': email,
        'password': password
    })


def getUser(username):
    userData = users.find_one({'_id': username})
    if(userData):
        return User(userData['email'], userData['_id'], userData['password'])
    else:
        return None


def saveRoom(roomName, roomOwner, roomMembers, roomPass):
    ID = ObjectId()
    rooms.insert_one({
        '_id': ID,
        'roomName': roomName,
        'roomOwner': roomOwner,
        'roomMembers': roomMembers,
        'roomPass': roomPass,
        'createdAt': datetime.now()
    })
    return ID

def validateMember(roomMember):
    return getUser(roomMember)

#def addMember(roomID, roomName, username, addedBy, mod=False):

