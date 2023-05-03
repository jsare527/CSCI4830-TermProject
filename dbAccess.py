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
roomMessages = db.get_collection("Messages")
friendRequests = db.get_collection("FriendRequests")


def saveUser(email, username, password):
    users.insert_one({
        '_id': username,
        'email': email,
        'password': password,
        'friendsList': [],
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

def getOwner(roomID):
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomOwner']

#appending owner to the roomMembers array, so we get an accurate count of users in a room.
def getRooms(username):
    memberOf = []
    ownerOf = []
    for room in rooms.find({'roomMembers': {"$all": [f'{username}']}}):
        room['roomMembers'].append(room['roomOwner'])
        memberOf.append(room)
    for room in rooms.find({'roomOwner': username}):
        room['roomMembers'].append(room['roomOwner'])
        ownerOf.append(room)
    return memberOf, ownerOf


def saveMessage(roomID, message, username):
    roomMessages.insert_one({
        'roomID': roomID,
        'message': message,
        'username': username,
        'sentAt': datetime.now(),
        'hourMinute': datetime.now().strftime("%H:%M")
    })

def getMessages(roomID):
    return list(roomMessages.find({
        'roomID': roomID
    }))

def getRoomName(roomID):
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomName']

def getRoomMembers(roomID):
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomMembers']

def deleteRoom(roomID):
    roomMessages.delete_many({
        'roomID': roomID
    })
    rooms.delete_one({
        '_id': ObjectId(roomID)
    })

#removes one member
def removeMember(roomID, username):
    rooms.update_one(
        {'_id': ObjectId(roomID)},
        {'$pull': {'roomMembers': username}}
    )
    roomMessages.delete_many({
        'roomID': roomID,
        'username': username,
    })

#removes multiple members at once
def removeMembers(roomID, roomMembers):
    for member in roomMembers:
        rooms.update_one(
            {'_id': ObjectId(roomID)},
            {'$pull': {'roomMembers': member}}
        )

#adds one user to a room
def addMember(roomID, username):
    rooms.update_one(
        {'_id': ObjectId(roomID)},
        {'$push': {'roomMembers': username}}
    )

#adds multiple members at once
def addMembers(roomID, roomMembers):
    for member in roomMembers:
        rooms.update_one(
            {'_id': ObjectId(roomID)},
            {'$push': {'roomMembers': member}}
        )

def removeMessage(roomID, msgID):
    roomMessages.delete_one({
        'roomID': roomID,
        '_id': ObjectId(msgID)
    })


#Updates room owner to the first member that exists in the "roomMembers array"
def updateOwner(roomID):
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    newOwner = result['roomMembers'][0]
    if(newOwner):
        rooms.update_one(
            {'_id': ObjectId(roomID)},
            {
            '$set': {'roomOwner': newOwner},
            '$pull': {'roomMembers': newOwner}
            },
        )
    else:
        deleteRoom(roomID)

#Creates a new model for a friend request.
#Sender: The user that sent the request
#Recipient: The user that receives the friend request
def sendFriendRequest(sender, recipient):
    friendRequests.insert_one({
        'sender': sender,
        'recipient': recipient,
        'sentAt': datetime.now(),
        'hourMinute': datetime.now().strftime("%H:%M")
    })

#Boolean function that tries to find a pending friend request.
#If it finds a request --> return the request's ID
#If it doesn't find a request --> return null
def isPending(sender, recipient):
    result = friendRequests.find_one({
        'sender': sender,
        'recipient': recipient
    })
    if(result):
        return result['_id']
    else:
        return None

def getIncomingRequests(username):
    return list(friendRequests.find({
        'recipient': username
    }))

def getOutGoingRequests(username):
    return list(friendRequests.find({
        'sender': username
    }))

def getFriends(username):
    result = users.find_one({
        '_id': username
    })
    return result['friendsList']

def isFriend(username, friend):
    result = users.find_one({
        '_id': username,
        'friendsList': {'$all': [f'{friend}']}
    })
    return result

def removeFriend(user, friend):
    users.update_one(
        {'_id': user},
        {'$pull': {'friendsList': friend}}
    )

def addFriend(requestID, recipient, sender):
    users.update_one(
        {'_id': recipient},
        {'$push': {'friendsList': sender}}
    )
    users.update_one(
        {'_id': sender},
        {'$push': {'friendsList': recipient}}
    )
    deleteFriendRequest(requestID)

def isRecipient(requestID, username):
    result = friendRequests.find_one({
        '_id': ObjectId(requestID)
    })
    return username == result['recipient']

def isSender(requestID, username):
    result = friendRequests.find_one({
        '_id': ObjectId(requestID)
    })
    return username == result['sender']

def deleteFriendRequest(requestID):
    friendRequests.delete_one({
        '_id': ObjectId(requestID)
    })
