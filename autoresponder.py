#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
import imaplib
import smtplib
import email
import time
import sys
import yaml
import argparse
import logging
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
    logging.info("Connecting to %s:%i as %s" % (imapConfig["server"],
            imapConfig["port"], imapConfig["username"]))
    imapServer = makeIMAPServer(imapConfig["server"],
            imapConfig["port"], imapConfig["ssl"], imapConfig["username"],
            imapConfig["password"])
    return imapServer


def makeSMTPServerWithConfig(smtpConfig):
    logging.info("Connecting to %s:%i as %s" % (smtpConfig["server"],
            smtpConfig["port"], smtpConfig["username"]))
    smtpServer = makeSMTPServer(smtpConfig["server"],
            smtpConfig["port"], smtpConfig["ssl"], smtpConfig["username"],
            smtpConfig["password"])
    return smtpServer

# pragma mark - IMAP Utils


def hasNewMail(imapServer):
    status, data = imapServer.status('INBOX', '(UNSEEN)')
    logging.debug("%s %s" % (status, data))
    unreadcount = int(data[0].split()[2].strip(').,]'))
    logging.info("There are %i unseen emails" % unreadcount)
    return unreadcount > 0


def UIDsForNewEmail(imapServer):
    status, data = imapServer.uid('search', None, '(UNSEEN)')
    logging.debug("%s %s" % (status, data))
    uids = data[0].split()
    return uids


def emailForUID(uid, imapServer):
    logging.info("Fetching email with uid: %s", uid)
    status, data = imapServer.uid('fetch', uid, '(RFC822)')
    logging.debug("%s" % status)
    raw_email = data[0][1]
    emailObj = email.message_from_string(raw_email)
    logging.info("From: %s. Subject: %s" % (emailObj['From'],
        emailObj['Subject']))
    return emailObj


#pragma mark -


def replyWithOriginalEmail(emailObj, fromAddress, body):
    logging.info("Creating reply")
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
    parser.add_argument('config', type=file, help="YAML configuration file")
    parser.add_argument('--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
        'CRITICAL'], type=(lambda string: string.upper()),
        help="Set the log level.")
    return parser.parse_args()


def setupLogging(loglevel):
    if loglevel:
        numeric_level = getattr(logging, loglevel, None)
        logging.basicConfig(level=numeric_level)


def main():
    args = parseArgs()
    setupLogging(args.log)
    logging.debug(args)
    config = yaml.load(args.config)
    logging.debug(config)
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
                logging.info("Email sent")
            smtpServer.quit()
        imapServer.close()
        imapServer.logout()
        logging.info("We're all done here")


if __name__ == "__main__":
    sys.exit(main())
