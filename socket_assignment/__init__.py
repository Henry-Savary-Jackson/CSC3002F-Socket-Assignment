# global dictionaries to be used across the application
users = dict() # stores users and their info (public_key, ip, port, etc...)
media = dict() # store the type, filename and data of all files received.
unacked_messages = dict() # stores messages that are awaiting a reply, but have not yet received a response

connections = dict() # store the socket object and the corresponding user , indexed by connection_id
group_chats =dict()  # stores all the chats and their messages and members

# Do note that these are usedby both the central server and clients