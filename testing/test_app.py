import pytest
import sys
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
sys.path.insert(1, '/home/admin/Python/FLASK/TermProject')
from dbAccess import *
#DELETE THE ROOM BEFOR TESTING
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--no-sandbox')


@pytest.fixture(scope="function")
def driver():
    driver = webdriver.Chrome("chromedriver", options=chrome_options)
    driver.implicitly_wait(4)
    driver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/")
    driver.implicitly_wait(4)
    yield driver
    driver.quit()

#Fixture to handle the login phase for testing.
@pytest.fixture(scope="function")
def firstAccountDriver(driver):
    username = "SeleniumBot"
    password = "password123"
    
    driver.find_element(By.XPATH, "//input[@id='username']").send_keys(username)
    driver.find_element(By.XPATH, "//input[@id='password']").send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(text(),'Log in')]").click()
    yield driver
    driver.quit()

@pytest.fixture(scope="function")
def secondAccountDriver(driver):
    username = "jurhe1"
    password = "test"

    driver.find_element(By.XPATH, "//input[@id='username']").send_keys(username)
    driver.find_element(By.XPATH, "//input[@id='password']").send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(text(),'Log in')]").click()
    yield driver
    driver.quit()


def test_url(driver):
    currentUrl = driver.current_url
    assert "http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/login?next=%2F" == currentUrl

class TestSignUp:
    
    email = "SeleniumBot@gmail.com"
    username = "SeleniumBot"
    password = "password123"
    
    #When it comes to actual test, delete seleniumbot user.
    @pytest.mark.skip
    def test_goodSignup(self, driver):
        #Test to see if signup page works - registers new user and redirects to the front page.
        signupButton = driver.find_element(By.XPATH, "//a[contains(text(),'New? Sign up!')]").click()
        driver.find_element(By.XPATH, "//input[@id='email']").send_keys(self.email)
        driver.find_element(By.XPATH, "//input[@id='username']").send_keys(self.username)
        driver.find_element(By.XPATH, "//input[@id='password']").send_keys(self.password)
        registerButton = driver.find_element(By.XPATH, "//button[contains(text(),'Sign up')]").click()
        text = driver.find_element(By.TAG_NAME, "body").text
        assert "Username already exists" not in text
        assert "Welcome to this chat app" in text

        #Check if user exists in database
        assert getUser(self.username) != None


    def test_badSignup(self, driver):
        #Bad sign up happens when the username chosen is one that is already in use. I'm going to use the username from the above function to test.
        signupButton = driver.find_element(By.XPATH, "//a[contains(text(),'New? Sign up!')]").click()
        driver.find_element(By.XPATH, "//input[@id='email']").send_keys(self.email)
        driver.find_element(By.XPATH, "//input[@id='username']").send_keys(self.username)
        driver.find_element(By.XPATH, "//input[@id='password']").send_keys(self.password)
        registerButton = driver.find_element(By.XPATH, "//button[contains(text(),'Sign up')]").click()
        text = driver.find_element(By.TAG_NAME, "body").text
        assert "Username already exists" in text
        assert "Welcome to this chat app" not in text

class TestLogin:
    username = "SeleniumBot"
    password = "wrongPassword"

    def test_goodLogin(self, firstAccountDriver):
        #Successful login
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Failed to login: Invalid username or password" not in text
        assert "Welcome to this chat app" in text

    def test_badLogin(self, driver):
        #Unsuccessful login

        driver.find_element(By.XPATH, "//input[@id='username']").send_keys(self.username)
        driver.find_element(By.XPATH, "//input[@id='password']").send_keys(self.password)
        driver.find_element(By.XPATH, "//button[contains(text(),'Log in')]").click()
        text = driver.find_element(By.TAG_NAME, "body").text
        assert "Welcome to this chat app" not in text
        assert "Failed to login: Invalid username or password" in text

class TestFriendFunctionality:
    currentUser = "SeleniumBot"
    validUsername = "jurhe1"
    invalidUsername = "fakeAccount"


    def sendValidRequest(self, firstAccountDriver):
        firstAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/find-friends")
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Find user" in text
        firstAccountDriver.find_element(By.XPATH, "//input[@id='friendUser']").send_keys(self.validUsername)
        firstAccountDriver.find_element(By.XPATH, "//button[contains(text(),'Send request')]").click()

    def sendInvalidRequest(self, firstAccountDriver):
        firstAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/find-friends")
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Find user" in text
        firstAccountDriver.find_element(By.XPATH, "//input[@id='friendUser']").send_keys(self.invalidUsername)
        firstAccountDriver.find_element(By.XPATH, "//button[contains(text(),'Send request')]").click()

    def test_sendFriendRequest(self, firstAccountDriver):
        if(isFriend(self.currentUser, self.validUsername)):
            removeFriend(self.currentUser, self.validUsername)
        
        self.sendInvalidRequest(firstAccountDriver)
        assert f"Username: {self.invalidUsername} does not exist"

        #Send successful friend request
        self.sendValidRequest(firstAccountDriver)
        #isPending(sender, recipient) sees if there is an outgoing friend request between two users.
        assert isPending(self.currentUser, self.validUsername) is not None

        #Try sending friend request to same user.
        self.sendValidRequest(firstAccountDriver)
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert f"You already have a pending friend request to {self.validUsername}"

    #Use second account to decline friend request.
    def test_declineFriendRequest(self, secondAccountDriver):
        secondAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/view-friends")
        text = secondAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Incoming friend requests" in text

        secondAccountDriver.find_element(By.XPATH, "//body[1]/div[1]/div[1]/div[1]/ul[1]/li[1]/div[1]/button[2]").click()
        assert isPending(self.currentUser, self.validUsername) == None

    def test_sendAnotherRequest(self, firstAccountDriver):
        self.sendValidRequest(firstAccountDriver)
        assert isPending(self.currentUser, self.validUsername)

    def test_acceptFriendRequest(self, secondAccountDriver):
        secondAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/view-friends")
        text = secondAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "You have no friends" in text

        secondAccountDriver.find_element(By.XPATH, "//body[1]/div[1]/div[1]/div[1]/ul[1]/li[1]/div[1]/button[1]").click()
        assert isPending(self.currentUser, self.validUsername) == None
        assert isFriend(self.currentUser, self.validUsername)
        


        



    

class TestCreateRoom:
    #If you want multiple room members, split names by comma. Ex: "jsare527, jsare123, etc." Usernames have to be valid, registered users.
    roomMembers = "jsare527, test123"
    roomOwner = "SeleniumBot"
    roomName = "Selenium bot"

    #-------FIXTURES-------#
    @pytest.fixture
    def createRoomDriver(self, firstAccountDriver):
        firstAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/create-room")
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Create a room" in text
        #Enters a room name, and room members into the fields. Then clicks the 'create' button.
        firstAccountDriver.find_element(By.XPATH, "//input[@id='roomName']").send_keys(self.roomName)
        firstAccountDriver.find_element(By.XPATH, "//input[@id='roomMembers']").send_keys(self.roomMembers)
        firstAccountDriver.find_element(By.XPATH, "//button[contains(text(),'Create')]").click()
        yield firstAccountDriver
        firstAccountDriver.quit()

    #-------TEST_CASES-------#


    def test_successfulCreateRoom(self, createRoomDriver):
        #Grabs the ID of the room. If there is no room, 'roomExists' returns None.
        roomID = roomExists(self.roomName, self.roomOwner)
        text = createRoomDriver.find_element(By.TAG_NAME, "body").text

        assert roomID is not None
        assert isOwner(roomID, self.roomOwner) is not None
        for member in self.roomMembers.split(','):
            assert isMember(roomID, member.strip())


    def test_existingRoomName(self, createRoomDriver):
        #After the room is created, have the bot try and recreate the same room.
        text = createRoomDriver.find_element(By.TAG_NAME, "body").text

        assert roomExists(self.roomName, self.roomOwner) is not None
        assert f"You already have a room named: {self.roomName}" in text

    def test_entersOwnUsername(self, firstAccountDriver):
        self.roomName = "RoomName2"
        self.roomMembers = "SeleniumBot, jsare527"
        #Test the case where user enters their own username in the 'room members' field.
        firstAccountDriver.get("http://ec2-18-223-126-81.us-east-2.compute.amazonaws.com:5000/create-room")
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Create a room" in text
        
        #Enters a room name, and room members into the fields. Then clicks the 'create' button.
        firstAccountDriver.find_element(By.XPATH, "//input[@id='roomName']").send_keys(self.roomName)
        firstAccountDriver.find_element(By.XPATH, "//input[@id='roomMembers']").send_keys(self.roomMembers)
        firstAccountDriver.find_element(By.XPATH, "//button[contains(text(),'Create')]").click()
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Cannot add your own username to room" in text


class TestRoomFunctions:
    roomMembers = "jsare527, test123"
    roomOwner = "SeleniumBot"
    roomName = "Selenium bot"
    messageSent = "This is the selenium bot talking"

    @pytest.fixture
    def joinRoomDriver(self, firstAccountDriver):
        #firstAccountDriver gets us past the login page and into the frontpage of the web app. From there, we look for certain elements.
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Failed to login: Invalid username or password" not in text
        assert "Welcome to this chat app" in text

        #Clicks on the "view your rooms" button.
        firstAccountDriver.find_element(By.XPATH, "//body/div[1]/div[1]/p[2]/a[1]").click()
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Member of" in text

        #Joins the room created by the bot.
        firstAccountDriver.find_element(By.XPATH, "//body/div[1]/div[2]/div[1]/ul[1]/li[1]/div[1]/button[1]").click()
        yield firstAccountDriver
        firstAccountDriver.quit()
    
    def test_joinRoom(self, joinRoomDriver):
        text = joinRoomDriver.find_element(By.TAG_NAME, "body").text
        assert f"Welcome to {self.roomName}" in text

    def test_sendMessage(self, joinRoomDriver):
        #Grab the roomID
        roomID = roomExists(self.roomName, self.roomOwner)
        text = joinRoomDriver.find_element(By.TAG_NAME, "body").text
        assert f"Welcome to {self.roomName}" in text

        #Sends a message to the room.
        joinRoomDriver.find_element(By.XPATH, "//input[@id='messageInput']").send_keys(self.messageSent)
        joinRoomDriver.find_element(By.XPATH, "//button[@id='inpBtn']").click()
        #Database function to get a room's messages. The ID below is the community room's ID. 
        #Get the last message sent to the room, which our bot sends.
        room_messages = getMessages(f"{roomID}")
        lastMessage = room_messages[len(room_messages)-1]['message']
        assert f"{self.messageSent}" == lastMessage


class TestManageRoom:
    #New members that we'll add through the management console. Have to be valid, registered users.
    friend = "jurhe1"
    newMembers = "klokman123, user1"
    roomMembers = "jsare527, test123"
    roomOwner = "SeleniumBot"
    roomName = "Selenium bot"
    friendMessage = "This is your friend talking."

    @pytest.fixture
    def manageRoomDriver(self, firstAccountDriver):
        #firstAccountDriver gets us past the login page and into the frontpage of the web app. From there, we look for certain elements.
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Failed to login: Invalid username or password" not in text
        assert "Welcome to this chat app" in text

        #Clicks on the "view your rooms" button.
        firstAccountDriver.find_element(By.XPATH, "//body/div[1]/div[1]/p[2]/a[1]").click()
        text = firstAccountDriver.find_element(By.TAG_NAME, "body").text
        assert "Member of" in text

        #Clicks on the 'manage room' button.
        firstAccountDriver.find_element(By.XPATH, "//body[1]/div[1]/div[2]/div[1]/ul[1]/li[1]/div[1]/button[2]").click()
        yield firstAccountDriver
        firstAccountDriver.quit()

    def addMembers(self, manageRoomDriver):
        manageRoomDriver.find_element(By.XPATH, "//input[@id='roomAdd']").send_keys(self.newMembers)
        manageRoomDriver.find_element(By.XPATH, "//button[contains(text(),'Add')]").click()

    def removeMembers(self, manageRoomDriver):
        manageRoomDriver.find_element(By.XPATH, "//input[@id='roomRemove']").send_keys(self.newMembers)
        manageRoomDriver.find_element(By.XPATH, "//button[contains(text(),'Remove')]").click()

    def addFriend(self, manageRoomDriver):
        self.removeMembers(manageRoomDriver)
        friendTag = manageRoomDriver.find_element(By.XPATH, "//body[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/li[1]/b[1]").text
        #friendTag will be in the form '{friendName} - Remove'.
        friendName = friendTag.split("-")[0].strip()
        manageRoomDriver.find_element(By.XPATH, "//body[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/li[1]/b[1]/a[1]").click()
        return friendName

    #Test to see if our driver leads us to the management console for the room.
    def test_Driver(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        #If the friend is already in the room, remove them first for testing.
        if(isMember(roomID, self.friend)):
            removeMember(roomID, self.friend)
        text = manageRoomDriver.find_element(By.TAG_NAME, "body").text
        assert f"Management for {self.roomName}" in text

    #Test case to add more members to a room through the management console.
    def test_AddMembers(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        self.addMembers(manageRoomDriver)
        #Loop through new members added, check if they are now members of the room with the isMember() database function. 
        for member in self.newMembers.split(','):
            assert isMember(roomID, member.strip())

    #Owners are able to quick add their friends. Only friend that 'SeleniumBot' has is 'jurhe1'.
    def test_AddFriend(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        friendName = self.addFriend(manageRoomDriver)
        assert isMember(roomID, friendName)


    #Test cases to remove members from a room using the management console. There are two possible ways to remove users.
     #------------------------------------------------------------------------------------------------------------------#
    #Owner can remove a room member by clicking the 'remove' tag next to a room member's name.
    def test_RemoveOneMember(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        self.addMembers(manageRoomDriver)
        totalMemberCount = len(getRoomMembers(roomID))
        #Deletes n members we added.
        n = 3
        for memberIndex in range(totalMemberCount, totalMemberCount - n, -1):
            manageRoomDriver.find_element(By.XPATH, f"//body/div[1]/div[3]/div[2]/div[1]/div[1]/div[{memberIndex}]/li[1]/b[1]/a[1]").click()

        #Check if new members were removed.
        for member in self.newMembers.split(','):
            assert isMember(roomID, member.strip()) == None

    #This function allows the owner to remove multiple members at once with comma split usernames.
    def test_RemoveMultipleMembers(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        self.addMembers(manageRoomDriver)
        self.removeMembers(manageRoomDriver)
        #Check and see if the new users are removed from the rooms. isMember() will return 'None' if they don't exist within a room.
        for member in self.newMembers.split(','):
            assert isMember(roomID, member.strip()) == None

    def test_addFriendAgain(self, manageRoomDriver):
        self.test_AddFriend(manageRoomDriver)

    def test_friendSendMessage(self, secondAccountDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        secondAccountDriver.find_element(By.XPATH, "//body/div[1]/div[1]/p[2]/a[1]").click()
        secondAccountDriver.find_element(By.XPATH, f"//a[contains(text(),'{self.roomName} - {roomID}')]").click()
        secondAccountDriver.find_element(By.XPATH, "//input[@id='messageInput']").send_keys(self.friendMessage)
        secondAccountDriver.find_element(By.XPATH, "//button[@id='inpBtn']").click()
        room_messages = getMessages(f"{roomID}")
        lastMessage = room_messages[len(room_messages)-1]['message']
        assert f"{self.friendMessage}" == lastMessage

    def test_RemoveMessage(self, manageRoomDriver):
        roomID = roomExists(self.roomName, self.roomOwner)
        manageRoomDriver.find_element(By.XPATH, "//body[1]/div[1]/div[4]/div[1]/div[1]/div[1]/div[2]/li[1]/b[1]/a[1]").click()
        room_messages = getMessages(f"{roomID}")
        lastMessage = room_messages[len(room_messages)-1]['message']
        assert f"{self.friendMessage}" != lastMessage

    #Deletes the room and all of it's contents.
    def test_DeleteRoom(self, manageRoomDriver):
        manageRoomDriver.find_element(By.XPATH, "//button[contains(text(),'Delete room')]").click()
        manageRoomDriver.switch_to.alert.accept()
        assert roomExists(self.roomName, self.roomName) == None

        


