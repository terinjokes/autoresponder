import imaplib
import email
import gevent
import time
from gevent import monkey
from gevent.timeout import Timeout

SERVER = "imap.gmail.com"
USERNAME = "user@domain.tld"
PASSWORD = "secret"

monkey.patch_all()

def idle(connection):
    tag = connection._new_tag()
    print "sending idle command"
    connection.send("%s IDLE\r\n" % tag)
    response = connection.readline()
    connection.loop = True

    if response == "+ idling\r\n":
        print "idling!"
        while connection.loop:
            resp = connection.readline()
            sid, message = resp[2:-2].split(' ')
            if message == "EXISTS":
                print "new message"
                handleNewEmail(connection, sid)
    else:
        raise Exception("IDLE not handled? : %s" % response)

def done(connection):
    print "done"
    connection.send("DONE\r\n")
    connection.loop = False
    connection.readline() #otherwise imaplib.idle() freaks out

def bounceIdle(connection, timeout):
    while True:
        with Timeout(timeout, False):
            idle(connection)
        done(connection)

def handleNewEmail(connection, sid):
    results, data = connection.uid('fetch', sid, "(RFC822)")
    raw_email = data[0][1]
    email_message = email.message_from_string(raw_email)
    print email_message["To"]

def testGevent():
    while True:
        print "%s" % time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        gevent.sleep(1)

def startIMAPConnection():
    print "creating connection"
    m = imaplib.IMAP4_SSL(SERVER)
    print "logging in"
    m.login(USERNAME, PASSWORD)
    print "selecting mailbox"
    m.select()
    bounceIdle(m, 1*60)

gevent.joinall([
    gevent.spawn(testGevent),
    gevent.spawn(startIMAPConnection)
])

#get yaml configuration

#utilize blocks over configuration objects
    #start imap connection
    #select inbox
    #start idle with block
        #if message == EXISTS
            #get new message
            #do SMTP reply
