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
    <title>Reply Recorded - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>Reply Recorded</h1>
    <p><a href="/">Main page</a></p>
    <p>"""

trailer = """
    <p><a href="/">Main page</a></p>
  </body>
</html>
"""

form = cgi.FieldStorage()
if 'uid' not in form or 'p' not in form or 'agree' not in form:
    print "Missing parameters.  Please check the link.\n", trailer
    raise SystemExit
uid = form['uid'].value
secret = form['p'].value
reply = form['agree'].value
comment = ""
if 'comment' in form:
    comment = form['comment'].value

conn = mysql.connector.connect(**dbconfig)
cursor = conn.cursor()
q = "SELECT secret FROM users WHERE uid = %s"
cursor.execute(q, (uid,))
row = cursor.fetchone()
if not row:
    print "No such user.  Please check the link.\n", trailer
    raise SystemExit
if secret != row[0]:
    print "Password does not match.  Please check the link or\n"
    print '<a href="/cgi-bin/send-email.py?uid=%s">re-send' % (uid,)
    print "the agreement email</a>"
    print trailer
    raise SystemExit

today = datetime.datetime.today().date()
t = ("UPDATE users SET date_replied=%s, reply=%s, comment=%s"
     " WHERE uid=%s")
cursor.execute(t, (today, reply, comment, uid))
conn.commit()

print "Your reply has been recorded, thank you!", trailer
