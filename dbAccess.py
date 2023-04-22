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


def saveRoom(roomName, roomOwner, roomMembers):
    ID = ObjectId()
    rooms.insert_one({
        '_id': ID,
        'roomName': roomName,
        'roomOwner': roomOwner,
        'roomMembers': roomMembers,
        'createdAt': datetime.now()
    })
    return ID

def isMember(roomID, username):
    result = rooms.find_one({
        '_id': ObjectId(roomID),
        'roomMembers': {"$all": [f'{username}']}
    })
    return result

def isOwner(roomID, username):
    result = rooms.find_one({
        '_id': ObjectId(roomID),
        'roomOwner': username
    })
    return result

def getRooms(username):
    lst = []
    lst2 = []
    for room in rooms.find({'roomMembers': {"$all": [f'{username}']}}):
        lst.append({'roomName': room['roomName'], 'ID': room['_id']})
    for room in rooms.find({'roomOwner': username}):
        lst2.append({'roomName': room['roomName'], 'ID': room['_id']})
    return lst, lst2


