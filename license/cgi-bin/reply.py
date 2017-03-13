#! /usr/bin/env python

import cgi, cgitb
import mysql.connector
import datetime, os, re, subprocess, sys, string, random

cgitb.enable()

dbconfig = {
        'user': 'licensereader',
        'password': open('../ropass.txt').read().strip(),
        'database': 'license'
        }

print """Content-Type: text/html

<html>
  <head>
    <title>Reply - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>Reply</h1>
    <p><a href="/">Main page</a></p>
    """

trailer = """
    <p><a href="/">Main page</a></p>
  </body>
</html>
"""

form = cgi.FieldStorage()
if 'uid' not in form or 'p' not in form:
    print "Missing parameters.  Please check the link.\n", trailer
    raise SystemExit
uid = form['uid'].value
secret = form['p'].value

conn = mysql.connector.connect(**dbconfig)
cursor = conn.cursor()
q = "SELECT secret FROM users WHERE uid = %s"
cursor.execute(q, (uid,))
row = cursor.fetchone()
if not row:
    print "No such user.  Please check the link.\n", trailer
    raise SystemExit
if secret != row[0]:
    print "Password does not match.  Please check the link.\n", trailer
    raise SystemExit

print """
    <form action="/cgi-bin/receive-reply.py" method="GET">

    <p>
    I give permission for my contributions to be licensed under
    the Apache License (version 2):</br>
    <input type="radio" name="agree" value="y" checked>Yes<br>
    <input type="radio" name="agree" value="n" >No<br>
    <input type="hidden" name="uid" value="%s">
    <input type="hidden" name="p" value="%s">
    </p>

    <p>
    Additional comments (optional):<br>
    <input type="text" name='comment' maxlength='80' size='40'>
    </p>

    <button action="submit">Send answer</button>
    </form>
""" % (uid, secret)

print trailer
