from flask import Flask, render_template, redirect, url_for, request, session
from pymongo.errors import DuplicateKeyError
from flask_socketio import SocketIO, join_room
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from dbAccess import getUser, saveUser, saveRoom, isMember, isOwner, getRooms
import bson

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = "vvvvvvvvvvvvvv"
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@app.route('/')
@login_required
def frontpage():
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
            return redirect(url_for('frontpage'))
        except DuplicateKeyError:
            err = "Username already exists"
    return render_template('signup.html', message=err)

@app.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    err = ''
    if request.method == 'POST':
        roomName = request.form.get('roomName')
        ID = request.form.get('roomID')
        try:
            if(isMember(ID, current_user.username) or isOwner(ID, current_user.username)):
                return redirect(url_for('chatRoom', username=current_user.username, room=roomName, roomID=ID))
            else:
                err = 'You are not a member of this room'
        except bson.errors.InvalidId:
            err = 'Invalid ID'
            return render_template("join.html", message=err)
    return render_template("join.html", message=err)

@app.route('/chat/<room>/<roomID>')
@login_required
def chatRoom(room, roomID):
    return render_template('chat.html', username=current_user.username, room=room, roomID=roomID)

@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def createRoom():
    err = ''
    if request.method == 'POST':
        roomName = request.form.get('roomName')
        roomMembers = request.form.get('roomMembers').split(',')

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
        return redirect(url_for('chatRoom', username=current_user.username, room=roomName, roomID=ID))
    return render_template('createRoom.html', message=err)

@app.route('/view-room')
@login_required
def viewRooms():
    memberOf, ownerOf = getRooms(current_user.username)
    return render_template('viewRooms.html', memberOf=memberOf, ownerOf=ownerOf)

@socketio.on('join_room')
def handle_join(data):
    app.logger.info(f"{data['username']} has joined room {data['room']}")
    join_room(data['room'])
    socketio.emit('joined', data)

@socketio.on('sent_message')
def handle_sentMessage(data):
    app.logger.info(f"{data['username']} has sent a message to room {data['room']}: {data['message']}")
    socketio.emit('messageReceive', data, room=data['room'])

@login_manager.user_loader
def load_user(username):
    return getUser(username)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="192.168.1.230")