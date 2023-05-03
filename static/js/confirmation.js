function conf(roomID, owner, memberCount){
    var message = "";
    var confirmation = null;
    var leaveRoom = `/leave-room/${roomID}/${username}`;
    var deleteLocation = `/delete/${roomID}`;
    if(memberCount == 1){
        message = "This will delete the room, no other members exist, confirm?";
        confirmation = confirm(message);
        if(confirmation){
            window.location.href = deleteLocation;
        }
        return;
    }
    if(username == owner){
        message = "This will give ownership to the 2nd member of this room, confirm?";
        confirmation = confirm(message);
        if(confirmation){
            window.location.href = leaveRoom;
            return;
        }
    }else{
        message = "This will make you leave this room, confirm?";
        confirmation = confirm(message);
        if(confirmation){
            window.location.href = leaveRoom;
            return;
        }
    }
}

