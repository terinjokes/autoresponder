#!/usr/bin/python
# vim: set fileencoding=utf-8 :
import imaplib
import smtplib
import email
import time
import sys
import yaml
from email.mime.text import MIMEText
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

def makeIMAPConnection(server, port, ssl, username, password):
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

def makeSMTPConnection(server, port, ssl, username, password):
    smtpServer = smtplib.SMTP_SSL(server)
    smtpServer.login(username, password)
    return smtpServer

def genForConfig(config):
    for server in config:
        imapConfig = server["imap"]
        smtpConfig = server["smtp"]
        imapServer = makeIMAPConnection(imapConfig["server"],
                imapConfig["port"], imapConfig["ssl"], imapConfig["username"],
                imapConfig["password"]);
        smtpServer = makeSMTPConnection(smtpConfig["server"],
                smtpConfig["port"], smtpConfig["ssl"], smtpConfig["username"],
                smtpConfig["password"]);
        yield (imapServer, smtpServer, smtpConfig["from"], server["body"])
        imapServer.close()
        imapServer.logout()
        smtpServer.quit()

def main(args):
    fileObj = open(args[1], 'r')
    config = yaml.load(fileObj)
    for (imapServer, smtpServer, smtpFrom, emailBody) in genForConfig(config):
        if hasNewMail(imapServer):
            uids = UIDsForNewEmail(imapServer)
            for emailObj in genEmailForUIDs(uids, imapServer):
                replyObj = MIMEText(emailBody, _charset="utf-8")
                # TODO (Terin Stock): Do I need to ensure these are clean, or does
                # email handle that?
                replyObj['To'] = emailObj['From'] if emailObj['Reply-To'] != "None" else emailObj['Reply-To']
                replyObj['From'] = smtpFrom
                replyObj['Date'] = email.utils.formatdate(time.time(), True)
                replyObj['References'] = emailObj['Message-ID'] #According to jwz, RFC1036 allows us to truncate references as we see fit
                replyObj['In-Reply-To'] = emailObj['Message-ID']
                replyObj['Subject'] = emailObj['Subject']
                smtpServer.sendmail(FROM_HEADER, replyObj['To'], replyObj.as_string())
    fileObj.close()
    return None

if __name__ == "__main__":
    sys.exit(main(sys.argv))
