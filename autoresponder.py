import imaplib
import smtplib
import email

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
USERNAME = "user@domain.tld"
PASSWORD = "secret"


def makeConnection(server, username, password):
    imapServer = imaplib.IMAP4_SSL(server)
    imapServer.login(username, password)
    imapServer.select('INBOX')
    return imapServer

def hasNewMail(imapServer):
    status, data = imapServer.status('INBOX', '(UNSEEN)')
    unreadcount = int(data[0].split()[2].strip(').,]'))
    if unreadcount > 0:
        return True
    else:
        return False

def UIDsForNewEmail(imapServer):
    status, data = imapServer.uid('search', None, '(UNSEEN)')
    uids = data[0].split()
    return uids

def genEmailForUIDs(uids, imapServer):
    for uid in uids:
        _, data = imapServer.uid('fetch', uid, '(RFC822)')
        raw_email = data[0][1]
        emailObj = email.message_from_string(raw_email)
        yield emailObj


imapServer = makeConnection(SERVER, USERNAME, PASSWORD)
if hasNewMail(imapServer):
    uids = UIDsForNewEmail(imapServer)
    for emailObj in genEmailForUIDs(uids, imapServer):
        print emailObj['To']
