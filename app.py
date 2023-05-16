from flask import Flask, render_template, redirect, url_for, request, session, Response
from pymongo.errors import DuplicateKeyError
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from dbAccess import *
from datetime import datetime
import eventlet
from eventlet import wsgi
from config.config import SECRET_KEY


app = Flask(__name__)
app.secret_key = SECRET_KEY
socketio = SocketIO(app)
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

#Home page route
@app.route('/')
@login_required
def frontpage():
    updateSession()
    return render_template("frontPage.html")

#Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route with flask_login. Logs a registered user in.

    Form data
    ---------
        Form data comes from 'templates/login.html':
        1. username (Type: str)
        2. password (Type: str)

    Redirection
    -----------
        ---Success---
        REDIRECTED TO: / (Frontpage)
        1. If the user is already authenticated by flask_login:                                     Redirect user to frontpage
        2. If the user is a registered user and they entered the correct username and password:     Login the user, and redirect to the frontpage.

        ---Failure---
        REDIRECTED TO: /login
        1. If the user is not registered or enters the wrong username/password:                     Redirect back to the login page with an error message.

    Database functions used
    -----------------------
        1. getUser()
    """
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



#Logout route
@app.route("/logout")
@login_required
def logout():
    """Logout route with flask_login. Logs the user out of their current session.

    Functions
    ---------
    1. logout_user() from flask_login logs the user out of their current session.

    Redirection
    -----------
    REDIRECTED TO: /login
    1. Redirects logged out user to the /login view.
    """
    logout_user()
    return redirect(url_for('login'))

#Sign up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Registers a new user in the database 
    
    Form data
    ---------
        Form data comes from 'templates/signup.html':
        1. email    (Type: str)
        2. username (Type: str)(Must be unique)
        3. password (Type: str)

    Redirection
    -----------
        ---Success---
        REDIRECTED TO: / (Frontpage)
        1. If the user entered a unique username, along with an email and password; their data is stored so they can login later.

        ---Failure---
        REDIRECTED TO: /signup
        1. If the user entered a username that exists, an error message is displayed and they're redirected to the signup page.

    Database functions used
    -----------------------
        1. saveUser()
        2. getUser()
        3. addMember()
    """
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
            addMember("6451ac77f60befb5eed53346", user.username)
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

#Create room route
@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def createRoom():
    """Allows a user to create a new chat room. Once created, this user will be the owner of the room. 

    Important variables
    -------------------
        1. roomID:                  This is the room's unqiue identifier; it will be used to redirect users to a specific room.
        2. current_user.username:   This is the current user logged into the session.
    
    Form data
    ---------
        Form data comes from 'templates/createRoom.html'
        1. roomName    (type: str)
        2. roomMembers (type: list)

    Redirection
    ----------- 
        ---Success---
        REDIRECTION TO: /chat/<roomID>
        1. If the user doesn't enter any room members in the form:                     Skips over validation of roomMembers and redirects user to the chat room.
        2. If the user enters a list of room members they wish to add:                 Verifies that each username provided is a registered user.
        3. If the room members are valid usernames that exist:                         Saves the chat room in the database, and redirects user to the chat room.

        ---Failure---
        REDIRECTION TO: /create-room
        1. If the user enters their own username in the room members field:            Displays an error message 'Cannot add your own username to room', and redirects to /create-room.
        2. If a member in 'roomMembers' does not exist in the database:                Displays an error message 'Username not found', and redirects to /create-room.
    
    Database functions used
    -----------------------
        1. getUser(username)
        2. saveRoom(roomName, roomOwner, roomMembers)
    """
    err = ''
    if request.method == 'POST':
        roomName = request.form.get('roomName')
        roomMembers = request.form.get('roomMembers').split(',')
        usernames = []
        if roomName == "":
            err = 'Room name cannot be blank'
            return render_template('createRoom.html', message=err)
        if roomExists(roomName, current_user.username):
            err = f'You already have a room named: {roomName}'
            return render_template('createRoom.html', message=err)
        if len(roomMembers) == 1 and roomMembers[0] == "":
            pass
        else:
            usernames = [username.strip() for username in roomMembers]
            if(current_user.username in usernames):
                err='Cannot add your own username to room'
                return render_template('createRoom.html', message=err)
            #Loop through given usernames
            for username in usernames:
                if(getUser(username)):
                    pass
                else:
                    err=f'Username not found: {username}'
                    return render_template('createRoom.html', message=err)
        roomID = saveRoom(roomName, current_user.username, usernames)
        return redirect(url_for('chatRoom', roomID=roomID))
    return render_template('createRoom.html', message=err)


@app.route('/chat/<roomID>')
@login_required
def chatRoom(roomID):
    """This is the view for displaying the chat room.

    Parameters
    ---------- 
        1. roomID: a chat room's specific ID.

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /chat/<roomID>
        1. If the current user is a room member or the room owner: Redirect user to the chat room.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not a room member/owner:         Display user a "Not authorized" message with a 403 code.
    
    Database functions used
    -----------------------
        1. getRoomMembers(roomID)
        2. getOwner(roomID)
        3. getRoomName(roomID)
        4. getMessages(roomID)
    """
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



@app.route('/view-room')
@login_required
def viewRooms():
    """Function to display chat rooms that a user is a member / owner of

    Important variables
    -------------------
        1. memberOf: A list containing all of the chat rooms that the current user is a member of.
        2. ownerOf: A list containing all of the chat rooms that the current user is an owner of.

    Return
    ------
        1. Returns flask's render_template for 'viewRooms.hmtl'. This will display to the user all of their memberOf rooms and ownerOf rooms.
    
    Database functions used
    -----------------------
        1. getRooms() 
    """
    updateSession()
    memberOf, ownerOf = getRooms(current_user.username)
    return render_template('viewRooms.html', memberOf=memberOf, ownerOf=ownerOf)


@app.route('/manage/<roomID>')
@login_required
def manageRoom(roomID):
    """Function to display the management console for a room.

    Important variables
    -------------------
        1. current_user.username:   Current user of the session.

    Description
    -----------
       The management console allows the owner of the chat room to add members, remove members, remove chats, 
       and the option to delete the room.

    Parameters
    ---------- 
        1. roomID: a chat room's specific ID.

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /manage/<roomID>
        1. If the current user is the owner of the room:           Display the management console to the user.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the room owner:              Display user a "Not authorized" message with a 403 code.

    Database functions used
    -----------------------
        1. getRoomMembers(roomID)
        2. getOwner(roomID)
        3. getRoomName(roomID)
        4. getMessages(roomID)
        5. getFriends(username)
        6. isMember(roomID, username)
    
    """
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
    """Function that displays the friend search page, and processes friend requests.

    Important variables
    -------------------
        1. friendName:              The username that you are trying to friend.
        2. current_user.username:   Current user of the session.

    Form data
    ---------
        Form data comes from 'templates/findFriends.html':
        1. friendUser    (Type: str)

    Conditions
    ----------
        ---Success---
            1. If the user enters a valid, registered username with no errors:  Sends a friend request to the specified user.

        ---Failure---
            1. If the user enters their own name:                               Return an error message: 'Cannot add yourself as a friend'.
            2. If the user already has a pending friend request:                Return an error message: 'You already have a pending friend request to {friendName}'.
            3. If the user is already friends with the entered user:            Return an error message: 'You are friends with this user already'.

    Database functions used
    -----------------------
        1. getUser(username)
        2. isPending(sender, recipient)
        3. isFriend(username, friend)
        4. sendFriendRequest(sender, recipient)
    """
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
            if(isFriend(current_user.username, friendName)):
                err = f'You are friends with this user already'
                return render_template('findFriends.html', message=err)
            sendFriendRequest(current_user.username, friendName)
            updateSession()
        else:
            err = f'Username: {friendName} does not exist'
    return render_template('findFriends.html', message=err)

@app.route('/view-friends')
@login_required
def viewFriends():
    """Function to display friend requests and current friends.

    Important variables
    -------------------
        1. current_user.username:   Current user of the session.
        2. incomingFriendRequests:  List containing all incoming friend requests to the current user.
        3. outGoingFriendRequests:  List containing all outgoing friend requests sent by the current user.
        4. currentFriends:          List containing all of the current user's friends.

    Database functions used
    -----------------------
        1. getIncomingRequests(username)
        2. getOutGoingRequests(username)
        3. getFriends(username)

    Return
    ------
        1. Returns flask's render_template of 'viewFriends.html' with all of the lists.
    
    """
    updateSession()
    incomingFriendRequests = getIncomingRequests(current_user.username)
    outGoingFriendRequests = getOutGoingRequests(current_user.username)
    currentFriends = getFriends(current_user.username)
    return render_template('viewFriends.html', incomingFriendRequests=incomingFriendRequests, outGoingFriendRequests=outGoingFriendRequests, currentFriends=currentFriends)

@app.route('/accept/<requestID>/<sender>')
@login_required
def handleAcceptRequest(requestID, sender):
    """Function to handle accepting friend requests.

    Description
    -----------
        The purpose of this function is to check if the person accepting is the actual recipient. 
        If a random user knew the requestID, and sender variable values, they could type 'accept/requestID/sender' 
        in the search bar and accept without being the recipient.

    Parameters
    ----------
        1. requestID: The unique ID of the friend request sent. 
        2. sender:    User who sent the friend request. 

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /viewFriends
        1. If the current user is the recipient of the request:       Accept the friend request.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the recipient of the request:   Display user a "Not authorized" message with a 403 code.
    
    """
    if(isRecipient(requestID, current_user.username)):
        addFriend(requestID, current_user.username, sender)
        return(redirect(url_for('viewFriends')))
    else:
        return "Not authorized", 403

@app.route('/decline/<requestID>')
@login_required
def handleDeclineRequest(requestID):
    """Function to handle accepting friend requests.

    Description
    -----------
        Purpose of this function is to check if the user declining the request is the sender or recipient of the friend request.
        If a random user knew the requestID without being a sender or recipient, they could type '/decline/requestID/' in the
        search bar and decline the request.

    Parameters
    ----------
        1. requestID: The unique ID of the friend request sent / received. 

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /viewFriends
        1. If the current user is the recipient of the request:                Decline the incoming friend request.
        2. If the current user is the sender of the request:                   Decline the outgoing friend request.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the recipient / sender of the request:   Display user a "Not authorized" message with a 403 code.
    """
    if(isRecipient(requestID, current_user.username) or isSender(requestID, current_user.username)):
        deleteFriendRequest(requestID)
        return(redirect(url_for('viewFriends')))
    else:
        return "Not authorized", 403


@app.route('/delete/<roomID>')
@login_required
def handleDeleteRoom(roomID):
    """Function to handle deleting a room.

    Description
    -----------
        Random user could type '/delete/roomID/' of a specific room and delete it. This function stops that
        by checking if the user is the owner of the room.

    Parameters
    ----------
        1. roomID: The unique ID of a chat room. 

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /frontpage
        1. If the current user is the owner of the chat room:           Delete the room.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the owner of the chat room:       Display user a "Not authorized" message with a 403 code.
    """
    if currentUserisOwner(roomID):
        deleteRoom(roomID)
        return redirect(url_for('frontpage'))
    else:
        return "Not authorized", 403

@app.route('/removeMember/<username>/<roomID>')
@login_required
def handleRemoveMember(roomID, username):
    """Function to handle removing one member from a chat room.
 
    Parameters
    ----------
        1. roomID:     The unique ID of a chat room. 
        2. username:   The name of the user to remove.

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /manage/roomID/
        1. If the current user is the owner of the chat room:           Remove the specified user from the room.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the owner of the chat room:       Display user a "Not authorized" message with a 403 code.

    Database functions used
    -----------------------
        1. removeMember(roomID, username)
    
    """
    if currentUserisOwner(roomID):
        removeMember(roomID, username)
        return(redirect(url_for('manageRoom', roomID=roomID)))
    else:
        return "Not authorized", 403

@app.route('/removeMembers/<roomID>', methods=['GET', 'POST'])
@login_required
def handleRemoveMembers(roomID):
    """Function to remove multiple members at once with form data.

    Parameters
    ----------
        1. roomID: The unique ID of a chat room.

    Form data
    ---------
        Form data comes from 'templates/manageRoom.html':
        1. roomRemove  (Type: str)

    Important variables
    -------------------
        1. roomMembers: Contains a string with comma delimited names. Ex: 'jsare527, jurhe1, test123'. 
        2. usernames:   The list of usernames after parsing commas and white space. Ex: ['jsare527', 'jurhe1', 'test123'].

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /manage/roomID/
        1. If the current user is the owner of the chat room:           Remove the specified users from the room.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the owner of the chat room:       Display user a "Not authorized" message with a 403 code.

    Database functions used
    -----------------------
        1. removeMembers(roomID, roomMembers)
    
    """
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
    """Function to add multiple members to a chat room at once. 

    Parameters
    ----------
        1. roomID: The unique ID of a chat room.

    Form data
    ---------
        Form data comes from 'templates/manageRoom.html':
        1. roomAdd  (Type: str)

    Important variables
    -------------------
        1. roomMembers: Contains a string with comma delimited names. Ex: 'jsare527, jurhe1, test123'. 
        2. usernames:   The list of usernames after parsing commas and white space. Ex: ['jsare527', 'jurhe1', 'test123'].

    Conditions
    ----------
        1. If a user in the list of names is already a member:                          Redirect to the management console, stopping the function.
        2. If a user is a valid, registered user and isn't a member of the chat room:   Add that user to the chat room.
        3. If you aren't the owner trying to add members:                               Redirect to 403 ERROR_CODE.
    
    """
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
    """Function to handle leaving a chat room.

    Parameters
    ----------
        1. roomID:      The unique ID of a chat room.
        2. username:    The username of the user leaving the room. 

    Conditions
    ----------
        1. If the owner is leaving the room with other members in the chat room:        Update the owner to the 2nd member of the chat room.
        2. If the owner is leaving the room with no other members in the chat room:     Delete the room.
        3. If a member is leaving the room:                                             Remove member from room.
        4. If you are not a member or owner of the chat room:                           Redirect to 403 ERROR_CODE.

    Database functions used
    -----------------------
        1. getOwner(roomID)
        2. updateOwner(roomID)
        3. removeMember(roomID, username)
    
    """
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
    """Function to remove a message sent in a chat room. 

    Parameters
    ----------
        1. roomID: The unique ID of a chat room
        2. msgID:  The unique ID of the message sent.

    Conditions
    ----------
        1. If the user removing the message is the owner:       Remove the message.
        2. If the user removing the message is not the owner:   Redirect them to a 403 ERROR_CODE.

    Database functions used
    -----------------------
        1. removeMessage(roomID, msgID)
    
    """
    if currentUserisOwner(roomID):
        removeMessage(roomID, msgID)
        return redirect(url_for('manageRoom', roomID=roomID))
    else:
        return "Not authorized", 403

@app.route('/removeFriend/<friend>')
@login_required
def handleRemoveFriend(friend):
    """Function to remove a friend.

    Execution
    ---------
        handleRemoveFriend() gets called when you click 'remove' next to a friend's name.

    Parameters
    ----------
        1. friend: The username of the friend you want to remove. 

    Important variables
    -------------------
        1. current_user.username:   Current user's username of the session.

    Redirection
    -----------
        ---Success---
        REDIRECTION TO: /view-friends
        1. If the current user is friends with the given 'friend' username:           Remove the friend from the current user's friend list.

        ---Failure---
        REDIRECTION TO: "Not authorized" ERROR_CODE: 403
        1. If the current user is not the owner of the chat room:                     Display user a "Not authorized" message with a 403 code.

    Database functions used
    -----------------------
        1. isFriend(username, friend)
        2. removeFriend(user, friend)
    
    """
    if isFriend(current_user.username, friend):
        removeFriend(current_user.username, friend)
        return redirect(url_for('viewFriends'))
    else:
        return "Not authorized", 403

@socketio.on('join_room')
def handle_join(data):
    join_room(data['room'])

@socketio.on('sent_message')
def handle_sentMessage(data):
    saveMessage(data['roomID'], data['message'], data['username'])
    data['hourMinute'] = datetime.now().strftime("%H:%M")
    socketio.emit('messageReceive', data, room=data['room'])

@login_manager.user_loader
def load_user(username):
    return getUser(username)

if __name__ == '__main__':
    socketio.run(app, host="ec2-18-223-126-81.us-east-2.compute.amazonaws.com", debug=True)