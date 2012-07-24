#!/usr/bin/python
# vim: set fileencoding=utf-8 :
import imaplib
import smtplib
import email
import time
from email.mime.text import MIMEText

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
USERNAME = "user@domain.tld"
PASSWORD = "secret"
FROM_HEADER = "Auto Responder User <user@domain.tld>"


def makeIMAPConnection(server, username, password):
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
        #handle moving out of inbox here

def makeSMTPConnection(server, username, password):
    smtpServer = smtplib.SMTP_SSL(server)
    smtpServer.login(username, password)
    return smtpServer


imapServer = makeIMAPConnection(IMAP_SERVER, USERNAME, PASSWORD)
if hasNewMail(imapServer):
    smtpServer = makeSMTPConnection(SMTP_SERVER, USERNAME, PASSWORD)
    uids = UIDsForNewEmail(imapServer)
    for emailObj in genEmailForUIDs(uids, imapServer):
        replyObj = MIMEText("Test Unicode Reply: ᛁᚳ᛫ᛗᚨᚷ᛫ᚷᛚᚨᛋ᛫ᛖᚩᛏᚪᚾ᛫ᚩᚾᛞ᛫ᚻᛁᛏ᛫ᚾᛖ᛫ᚻᛖᚪᚱᛗᛁᚪᚧ᛫ᛗᛖ᛬", "plain", "utf-8")
        # TODO (Terin Stock): Do I need to ensure these are clean, or does
        # email handle that?
        replyObj['To'] = emailObj['From'] if emailObj['Reply-To'] != "None" else emailObj['Reply-To']
        replyObj['From'] = FROM_HEADER
        replyObj['Date'] = email.utils.formatdate(time.time(), True)
        replyObj['References'] = emailObj['Message-ID'] #According to jwz, RFC1036 allows us to truncate references as we see fit
        replyObj['In-Reply-To'] = emailObj['Message-ID']
        replyObj['Subject'] = emailObj['Subject']
        smtpServer.sendmail(FROM_HEADER, replyObj['To'], replyObj.as_string())
    smtpServer.quit()
imapServer.close()
imapServer.logout()
