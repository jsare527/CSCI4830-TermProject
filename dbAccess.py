from pymongo import MongoClient
from bson import ObjectId
from userAuth import User
from datetime import datetime
from config.config import DB_PASSWORD

DB_ACCESS = f"mongodb+srv://jsare527:{DB_PASSWORD}@termproject.8hcqb9v.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(DB_ACCESS)

db = client.get_database("TermProject")
users = db.get_collection("Users")
rooms = db.get_collection("Rooms")
roomMessages = db.get_collection("Messages")
friendRequests = db.get_collection("FriendRequests")


def saveUser(email, username, password):
    """ 
    Function to register a new 'user' model in database.

    Variables come from form data.
    """
    users.insert_one({
        '_id': username,
        'email': email,
        'password': password,
        'friendsList': [],
    })


def getUser(username):
    """Function to find a specific user based off of their username. 
    Conditions
    ----------
        1. If the user is found, a new 'User' model is made from the class in 'userAuth.py'.
        2. If the user data is not found, returns None.

    User class
    ----------
        User class takes three parameters in it's constructor: email, username, password.
        This class is used with 'flask_login' to simplify logging in.
    """
    userData = users.find_one({'_id': username})
    if(userData):
        return User(userData['email'], userData['_id'], userData['password'])
    else:
        return None


def saveRoom(roomName, roomOwner, roomMembers):
    """Function to create or 'save' a new room.

    Parameters
    ----------
        1. roomName:    name of the room.
        2. roomOwner:   username of the owner.
        3. roomMembers: usernames of the room members. 
    """
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
    """ Function to determine if a username is a member of a chat room.
    Conditions
    ----------
        1. If a user is found in the chat room:         return chat room data.
        2. If a user is not found in the chat room:     return None. 
    """
    result = rooms.find_one({
        '_id': ObjectId(roomID),
        'roomMembers': {"$all": [f'{username}']}
    })
    return result

def isOwner(roomID, username):
    """Function to check if a user is the owner of a chat room. 

    Conditions
    ----------
        1. If an owner of the chat room matches the given username:     return chat room data.
        2. If an owner is not found with given username:                return None.
    """
    result = rooms.find_one({
        '_id': ObjectId(roomID),
        'roomOwner': username
    })
    return result

def getOwner(roomID):
    """Function to get an owner of a chat room. """
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomOwner']

#appending owner to the roomMembers array, so we get an accurate count of users in a room.
def getRooms(username):
    """Function to get any rooms that a user is either an owner or member of. 
    Returns
    -------
        1. memberOf: <list> containing all of the chat rooms the user is a member of.
        2. ownerOf:  <list> containing all of the chat rooms the user is an owner of.
    Extra note
    ----------
        I append the roomOwner to the list to get an accurate count of the amount of users in a room.
    """
    memberOf = []
    ownerOf = []
    for room in rooms.find({'roomMembers': {"$all": [f'{username}']}}):
        room['roomMembers'].append(room['roomOwner'])
        memberOf.append(room)
    for room in rooms.find({'roomOwner': username}):
        room['roomMembers'].append(room['roomOwner'])
        ownerOf.append(room)
    return memberOf, ownerOf

#If a room exists, we return the room's ID. Otherwise, return None.
def roomExists(roomName, roomOwner):
    """Function to check if a room exists with a given roomName and roomOwner. 
    Conditions
    ----------
        1. If a room is found with the given roomName and roomOwner: return the ID of the chat room.
        2. If a room is not found:                                   return None.
    """
    _, ownerOf = getRooms(roomOwner)
    for room in ownerOf:
        if room['roomName'] == roomName:
            return room['_id']
    return None


def saveMessage(roomID, message, username):
    """Function to save a message to a certain chat room. This allows for chat history to exist."""
    roomMessages.insert_one({
        'roomID': roomID,
        'message': message,
        'username': username,
        'sentAt': datetime.now(),
        'hourMinute': datetime.now().strftime("%H:%M")
    })

def deleteUserMessages(username):
    """Function to delete all messages sent by a user from a chat room. 
    Parameters
    ----------
        1. username: sender of the message.
    """
    roomMessages.delete_many({
        'username': username
    })

def getMessages(roomID):
    """ Function to get all messages sent to a room. """
    return list(roomMessages.find({
        'roomID': roomID
    }))

def getRoomName(roomID):
    """ Returns the chat room's name with given roomID. """
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomName']

def getRoomMembers(roomID):
    """ Returns a list of roomMembers of a given roomID. """
    result = rooms.find_one({
        '_id': ObjectId(roomID)
    })
    return result['roomMembers']

def deleteRoom(roomID):
    """Function to delete a room.
        When deleting a room, we have to delete all of the messages first, then delete the actual room.
    """
    roomMessages.delete_many({
        'roomID': roomID
    })
    rooms.delete_one({
        '_id': ObjectId(roomID)
    })

#removes one member from a specified room
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
        roomMessages.delete_many({
        'roomID': roomID,
        'username': member,
        })

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
    """Function to delete a message from a chat room. 
    Parameters
    ----------
        1. roomID: Unique ID of a chat room.
        2. msgID:  Unique ID of a message sent.
    """
    roomMessages.delete_one({
        'roomID': roomID,
        '_id': ObjectId(msgID)
    })


#Updates room owner to the first member that exists in the "roomMembers array"
def updateOwner(roomID):
    """Function to update the owner when the owner leaves the room.
    Conditions
    ----------
        1. If there are other room members in the room when the owner leaves: Update the owner to the 2nd room member.
        2. If there are no other room members:                                Delete the room.
    """
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
    """Returns a list of incoming friend requests."""
    return list(friendRequests.find({
        'recipient': username
    }))

def getOutGoingRequests(username):
    """Returns a list of outgoing friend requests. """
    return list(friendRequests.find({
        'sender': username
    }))

def getFriends(username):
    """Returns a list of friends from specified username."""
    result = users.find_one({
        '_id': username
    })
    return result['friendsList']

def isFriend(username, friend):
    """Function to determine if two users are friends.
    Conditions
    ----------
        1. If they are friends:         return user data.
        2. If they are not friends:     return None. 
    """
    result = users.find_one({
        '_id': username,
        'friendsList': {'$all': [f'{friend}']}
    })
    return result

def removeFriend(user, friend):
    """Function to remove a friend from friends list. 
    
    When one user removes a friend, it removes the friend from both users.
    """
    users.update_one(
        {'_id': user},
        {'$pull': {'friendsList': friend}}
    )
    users.update_one(
        {'_id': friend},
        {'$pull': {'friendsList': user}}
    )

def addFriend(requestID, recipient, sender):
    """Function to add a friend to both user's friends list."""
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
    """Funciton to check if a user is the recipient of a given request.
    Conditions
    ----------
        1. If they are the recipient:       Return True.
        2. If they are not the recipient:   Return False.
    """
    result = friendRequests.find_one({
        '_id': ObjectId(requestID)
    })
    return username == result['recipient']

def isSender(requestID, username):
    """Funciton to check if a user is the sender of a given request.
    Conditions
    ----------
        1. If they are the sender:       Return True.
        2. If they are not the sender:   Return False.
    """
    result = friendRequests.find_one({
        '_id': ObjectId(requestID)
    })
    return username == result['sender']

def deleteFriendRequest(requestID):
    """Deletes the incoming / outgoing friend request."""
    friendRequests.delete_one({
        '_id': ObjectId(requestID)
    })

#Removes a user from everyone's friend list
def removeAllFriends(username):
    for friend in users.find({'friendsList': {"$all": [f'{username}']}}):
        users.update_one(
            {'_id': friend['_id']},
            {'$pull': {'friendsList': username}}
        )

def cancelAllRequests(username):
    """Function to delete outgoing / incoming friend requests. """
    outgoingReq = getOutGoingRequests(username)
    incomingReq = getIncomingRequests(username)
    queue = outgoingReq + incomingReq
    for ID in queue:
        deleteFriendRequest(ID['_id'])



#Deletes a user. Makes them leave all rooms, removes all friends, and cancels all friend requests before deleting account.
def deleteAccount(username):
    memberRooms, ownerRooms = getRooms(username)
    cancelAllRequests(username)
    removeAllFriends(username)
    for memRoom in memberRooms:
        roomID = memRoom['_id']
        removeMember(roomID, username)
    for ownRoom in ownerRooms:
        roomID = ownRoom['_id']
        updateOwner(roomID)

    users.delete_one({
        '_id': username
    })

