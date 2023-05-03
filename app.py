from flask import Flask, render_template, redirect, url_for, request, session, Response
from pymongo.errors import DuplicateKeyError
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from dbAccess import *
from datetime import datetime
import bson

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = "vvvvvvvvvvvvvv"
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

#Helper functions below

#Checks if the current user is the owner of a given roomID
#When current user is the owner of the roomID --> returns True
#When current user is not the owner of the roomID --> returns False
def currentUserisOwner(roomID):
    return current_user.username == getOwner(roomID)

#function to update friend request variables on page refreshes/redirections
def updateSession():
    var = getIncomingRequests(current_user.username)
    var1 = getOutGoingRequests(current_user.username)
    session['incomingFriendRequests'] = len(var)
    session['outgoingFriendRequests'] = len(var1)


@app.route('/')
@login_required
def frontpage():
    updateSession()
    return render_template("base.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('frontpage'))
    err = ''
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        user = getUser(username)
        if user and user.checkPass(password):
            login_user(user)
            return redirect(url_for('frontpage'))
        else:
            err = "Failed to login: Invalid username or password"
    return render_template('login.html', message=err)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    err = ''
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            saveUser(email, username, password)
            user = getUser(username)
            login_user(user)

            #After user signs up, add them to the community room
            addMember("644ef8aa80633eb42e420aff", user.username)
            return redirect(url_for('frontpage'))
        except DuplicateKeyError:
            err = "Username already exists"
    return render_template('signup.html', message=err)

@app.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    err = ''
    if request.method == 'POST':
        ID = request.form.get('roomID')
        try:
            if(isMember(ID, current_user.username) or isOwner(ID, current_user.username)):
                return redirect(url_for('chatRoom', roomID=ID))
            else:
                err = 'You are not a member of this room'
        except bson.errors.InvalidId:
            err = 'Invalid ID'
            return render_template("join.html", message=err)
    return render_template("join.html", message=err)

@app.route('/chat/<roomID>')
@login_required
def chatRoom(roomID):
    updateSession()
    roomMembers = getRoomMembers(roomID)
    owner = getOwner(roomID)
    roomMembers.insert(0, owner + " (Owner)")
    if current_user.username in roomMembers or current_user.username == owner:
        roomName = getRoomName(roomID)
        messages = getMessages(roomID)
        return render_template('chat.html', username=current_user.username, roomName=roomName, roomID=roomID, messages=messages, members=roomMembers, owner=owner, memberCount=len(roomMembers))
    else:
        return "Not authorized", 403

@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def createRoom():
    err = ''
    if request.method == 'POST':
        roomName = request.form.get('roomName')
        roomMembers = request.form.get('roomMembers').split(',')
        usernames = []
        if len(roomMembers) == 1 and roomMembers[0] == "":
            pass
        else:
            usernames = [username.strip() for username in roomMembers]
            if(current_user.username in usernames):
                err='Cannot add your own username to room'
                return render_template('createRoom.html', message=err)
            for username in usernames:
                if(getUser(username)):
                    pass
                else:
                    err=f'Username not found: {username}'
                    return render_template('createRoom.html', message=err)
        ID = saveRoom(roomName, current_user.username, usernames)
        return redirect(url_for('chatRoom', roomID=ID))
    return render_template('createRoom.html', message=err)

@app.route('/view-room')
@login_required
def viewRooms():
    updateSession()
    memberOf, ownerOf = getRooms(current_user.username)
    return render_template('viewRooms.html', memberOf=memberOf, ownerOf=ownerOf)

@app.route('/manage/<roomID>')
@login_required
def manageRoom(roomID):
    updateSession()
    owner = getOwner(roomID)
    if currentUserisOwner(roomID):
        roomName = getRoomName(roomID)
        roomMembers = getRoomMembers(roomID)
        messages = getMessages(roomID)
        currentFriends = getFriends(current_user.username)
        nonMemberFriends = []
        for friend in currentFriends:
            if(isMember(roomID, friend)):
                continue
            else:
                nonMemberFriends.append(friend)
        return render_template('manageRoom.html', roomName=roomName, members=roomMembers, roomID=roomID, memberCount=len(roomMembers), messages=messages, messageCount=len(messages), nonMemberFriends=nonMemberFriends, friendCount=len(nonMemberFriends))
    else:
        return "Not authorized", 403

@app.route('/find-friends', methods=['GET', 'POST'])
@login_required
def findFriends():
    err = ''
    if request.method == 'POST':
        friendName = request.form.get('friendUser').strip()
        if friendName == current_user.username:
            err = 'Cannot add yourself as a friend'
            return render_template('findFriends.html', message=err)
        if getUser(friendName):
            if(isPending(current_user.username, friendName)):
                err = f'You already have a pending friend request to {friendName}'
                return render_template('findFriends.html', message=err)
            if(isPending(friendName, current_user.username)):
                err = f'This user has sent you a friend request already'
                return render_template('findFriends.html', message=err)
            sendFriendRequest(current_user.username, friendName)
            updateSession()
        else:
            err = f'Username: {friendName} does not exist'
    return render_template('findFriends.html', message=err)

@app.route('/view-friends')
@login_required
def viewFriends():
    updateSession()
    incomingFriendRequests = getIncomingRequests(current_user.username)
    outGoingFriendRequests = getOutGoingRequests(current_user.username)
    currentFriends = getFriends(current_user.username)
    return render_template('viewFriends.html', incomingFriendRequests=incomingFriendRequests, outGoingFriendRequests=outGoingFriendRequests, currentFriends=currentFriends)

@app.route('/accept/<requestID>/<sender>')
@login_required
def handleAcceptRequest(requestID, sender):
    if(isRecipient(requestID, current_user.username)):
        addFriend(requestID, current_user.username, sender)
        return(redirect(url_for('viewFriends')))
    else:
        return "Not authorized", 403

@app.route('/decline/<requestID>')
@login_required
def handleDeclineRequest(requestID):
    if(isRecipient(requestID, current_user.username) or isSender(requestID, current_user.username)):
        deleteFriendRequest(requestID)
        return(redirect(url_for('viewFriends')))
    else:
        return "Not authorized", 403


@app.route('/delete/<roomID>')
@login_required
def handleDeleteRoom(roomID):
    if currentUserisOwner(roomID):
        deleteRoom(roomID)
        return redirect(url_for('frontpage'))
    else:
        return "Not authorized", 403

@app.route('/removeMember/<username>/<roomID>')
@login_required
def handleRemoveMember(roomID, username):
    if currentUserisOwner(roomID):
        removeMember(roomID, username)
        return(redirect(url_for('manageRoom', roomID=roomID)))
    else:
        return "Not authorized", 403

@app.route('/removeMembers/<roomID>', methods=['GET', 'POST'])
@login_required
def handleRemoveMembers(roomID):
    if currentUserisOwner(roomID):
        if request.method == 'POST':
            roomMembers = request.form.get('roomRemove').split(",")
            usernames = [username.strip() for username in roomMembers]
            removeMembers(roomID, usernames)
            return redirect(url_for('manageRoom', roomID=roomID))
    else:
        return "Not authorized", 403

@app.route('/addMembers/<roomID>', methods=['GET', 'POST'])
@login_required
def handleAddMembers(roomID):
    if currentUserisOwner(roomID):
        if request.method == 'POST':
            roomMembers = request.form.get('roomAdd').split(",")
            usernames = [username.strip() for username in roomMembers]
            for username in usernames:
                if(isMember(roomID, username)):
                    return redirect(url_for('manageRoom', roomID=roomID))
                if(getUser(username)):
                    pass
                else:
                    return redirect(url_for('manageRoom', roomID=roomID))
            addMembers(roomID, usernames)
            return redirect(url_for('manageRoom', roomID=roomID))
    else:
        return "Not authorized", 403

@app.route('/addMember/<roomID>/<username>')
@login_required
def handleAddMember(roomID, username):
    if currentUserisOwner(roomID):
        addMember(roomID, username)
        return redirect(url_for('manageRoom', roomID=roomID))
    else:
        return "Not authorized", 403

@app.route('/leave-room/<roomID>/<username>')
@login_required
def handleLeaveRoom(roomID, username):
    if current_user.username == username:
        owner = getOwner(roomID)
        if(username == owner):
            updateOwner(roomID)
        else:
            removeMember(roomID, username)
        return redirect(url_for('viewRooms'))
    else:
        return "Not authorized", 403

@app.route('/removeMessage/<roomID>/<msgID>')
@login_required
def handleRemoveMessage(roomID, msgID):
    if currentUserisOwner(roomID):
        removeMessage(roomID, msgID)
        return redirect(url_for('manageRoom', roomID=roomID))
    else:
        return "Not authorized", 403

@app.route('/removeFriend/<friend>')
@login_required
def handleRemoveFriend(friend):
    if isFriend(current_user.username, friend):
        removeFriend(current_user.username, friend)
        return redirect(url_for('viewFriends'))
    else:
        return "Not authorized", 403

@socketio.on('join_room')
def handle_join(data):
    app.logger.info(f"{data['username']} has joined room {data['room']}")
    join_room(data['room'])

@socketio.on('sent_message')
def handle_sentMessage(data):
    app.logger.info(f"{data['username']} has sent a message to room {data['room']}: {data['message']}")
    saveMessage(data['roomID'], data['message'], data['username'])
    data['hourMinute'] = datetime.now().strftime("%H:%M")
    socketio.emit('messageReceive', data, room=data['room'])

@login_manager.user_loader
def load_user(username):
    return getUser(username)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="192.168.1.230")