#! /usr/bin/env python

import cgi, cgitb
import mysql.connector
import datetime, os, re, subprocess, sys, string, random

cgitb.enable()

dbconfig = {
        'user': 'license',
        'password': open('../rwpass.txt').read().strip(),
        'database': 'license'
        }

print """Content-Type: text/html

<html>
  <head>
    <title>Send email - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>Send email</h1>

    <p>"""

trailer = """
    </p>
    <p><a href="/">Main page</a></p>
  </body>
</html>
"""

whitelist = (
        "mark@awe.com",
        "openssl-users@dukhovni.org",
        "tjh@cryptsoft.com",
        "lutz@lutz-jaenicke.de",
        "ben@links.org",
        "marquess@openssl.com",
        "marquess@veridicalsystems.com",
        "kurt@roeckx.be",
        "richard@levitte.org",
        "levitte@lp.se",
        )

def okay_to_resend(email, last_asked):
    """Return 1 if okay to resend email."""
    if email[-12:] == '@openssl.org' or email in whitelist:
        return 1
    return 0

form = cgi.FieldStorage()
if 'uid' not in form:
    print "No user specified.\n", trailer
    raise SystemExit
uid = form['uid'].value

conn = mysql.connector.connect(**dbconfig)
cursor = conn.cursor()
q = "SELECT email, reply, last_asked, secret FROM users WHERE uid = %s"
cursor.execute(q, (uid,))
row = cursor.fetchone()
if not row:
    print "No such user.\n", trailer
    raise SystemExit
email, reply, last_asked, secret = row

#if reply == 'd':
#    print "Dev team, not sending.\n", trailer
#    raise SystemExit

if last_asked and not okay_to_resend(email, last_asked):
    diff = datetime.datetime.today().date() - last_asked
    days = diff.days
    print "Mail to", email, "was sent", str(last_asked) + ","
    if days == 0:
        print "earlier today.\n"
        print "Please wait a day before requesting again.", trailer
        raise SystemExit
    if days <= 2:
        print "recently.\n"
        print "Please wait a day before requesting again.", trailer
        raise SystemExit

d = { 'uid': uid, 'secret': secret }
raw = open("../request-approval.txt").read()

args = ('mail', '-s', 'OpenSSL License change',
        '-r', 'license@openssl.org', email)
f = subprocess.Popen(args, stdin=subprocess.PIPE).stdin
print >>f, raw % d
f.close()

today = datetime.datetime.today().date()
t = 'UPDATE users SET last_asked=%s WHERE uid=%s'
cursor.execute(t, (today, uid))
conn.commit()

print "Mail sent (with the fields filled in):</p>"
print "<pre>"
print raw
print "</pre>"
print "<p>"

print trailer
raise SystemExit
