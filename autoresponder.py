#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
import imaplib
import smtplib
import email
import time
import sys
import yaml
import argparse
from email.mime.text import MIMEText

# pragma mark - Server Connections


def makeIMAPServer(server, port, ssl, username, password):
    imapServer = (imaplib.IMAP4_SSL(server, port) if ssl else
            imaplib.IMAP(server, port))
    imapServer.login(username, password)
    imapServer.select('INBOX')
    return imapServer


def makeSMTPServer(server, port, ssl, username, password):
    smtpServer = (smtplib.SMTP_SSL(server, port) if ssl else
            smtplib.SMTP(server, port))
    smtpServer.login(username, password)
    return smtpServer


def makeIMAPServerWithConfig(imapConfig):
    imapServer = makeIMAPServer(imapConfig["server"],
            imapConfig["port"], imapConfig["ssl"], imapConfig["username"],
            imapConfig["password"])
    return imapServer


def makeSMTPServerWithConfig(smtpConfig):
    smtpServer = makeSMTPServer(smtpConfig["server"],
            smtpConfig["port"], smtpConfig["ssl"], smtpConfig["username"],
            smtpConfig["password"])
    return smtpServer

# pragma mark - IMAP Utils


def hasNewMail(imapServer):
    status, data = imapServer.status('INBOX', '(UNSEEN)')
    unreadcount = int(data[0].split()[2].strip(').,]'))
    return unreadcount > 0


def UIDsForNewEmail(imapServer):
    status, data = imapServer.uid('search', None, '(UNSEEN)')
    uids = data[0].split()
    return uids


def emailForUID(uid, imapServer):
    _, data = imapServer.uid('fetch', uid, '(RFC822)')
    raw_email = data[0][1]
    emailObj = email.message_from_string(raw_email)
    return emailObj


#pragma mark -


def replyWithOriginalEmail(emailObj, fromAddress, body):
    replyObj = MIMEText(body, _charset="utf-8")
    # TODO (Terin Stock): Do I need to ensure these are clean,
    # or does 'email' handle that?
    replyObj['To'] = emailObj['From']
    if emailObj['Reply-To'] != "None":
        replyObj['To'] = emailObj['Reply-To']
    replyObj['From'] = fromAddress
    replyObj['Date'] = email.utils.formatdate(time.time(), True)
    # According to jwz, RFC1036 allows us to truncate references
    # (http://www.jwz.org/doc/threading.html)
    replyObj['References'] = emailObj['Message-ID']
    replyObj['In-Reply-To'] = emailObj['Message-ID']
    replyObj['Subject'] = emailObj['Subject']
    return replyObj


def parseArgs():
    parser = argparse.ArgumentParser(description='Autorespond to new emails.')
    parser.add_argument('config', type=file)
    return parser.parse_args()


def main():
    args = parseArgs()
    config = yaml.load(args.config)
    args.config.close()
    for server in config:
        imapServer = makeIMAPServerWithConfig(server['imap'])
        if hasNewMail(imapServer):
            smtpServer = makeSMTPServerWithConfig(server['smtp'])
            uids = UIDsForNewEmail(imapServer)
            for uid in uids:
                emailObj = emailForUID(uid, imapServer)
                replyObj = replyWithOriginalEmail(emailObj,
                        server['smtp']['from'],
                        server['body'])
                smtpServer.sendmail(server['smtp']['from'],
                        replyObj['To'],
                        replyObj.as_string())
            smtpServer.quit()
        imapServer.close()
        imapServer.logout()


if __name__ == "__main__":
    sys.exit(main())
