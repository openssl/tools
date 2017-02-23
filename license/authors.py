#! /usr/bin/env python

import cgi
import cgitb
import mysql.connector

cgitb.enable()

urlbase = 'https://github.com/openssl/openssl/commit/'

dbconfig = {
        'user': 'licensereader',
        'password': open('../ropass.txt').read().strip(),
        'database': 'license'
        }
conn = mysql.connector.connect(**dbconfig)
cursor = conn.cursor()

header = """Content-Type: text/html

<html>
  <head>
    <title>Authors - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>%s</h1>

    <p>Names appear multiple times because of multiple email addresses.</p>
"""

trailer = """
    <a href="/">Main page</a>
  </body>
</html>
"""

def summary(h1, where):
    print header % (h1,)
    q = "SELECT name, uid FROM users " + where + " ORDER BY name"
    cursor.execute(q)
    print "<p class='cw'>"
    for row in cursor:
        name, uid = row
        name = name.encode('ascii', errors='xmlcharrefreplace')
        print '<a href="lookup.py?uid=%d">%s</a><br>' % (uid,name)
    print "</p>"
    print trailer

def details():
    print header % ("Response Details",)
    print "<table border='1' class='cw'>"
    print "<tr><th>Name</th><th>Reply</th><th>Date</th><th>Comment</th></tr>"
    q = ("SELECT name,uid,reply,date_replied,comment"
            " FROM users ORDER BY reply,name")
    cursor.execute(q)
    for row in cursor:
        name,uid,reply,date_replied,comment = row
        if comment is None or comment is '':
            comment = "--"
        print ("<tr>"
                "<td><a href='lookup.py?uid=%d'>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td></tr>") % (uid,name,reply,date_replied,comment)
    print "</table>"
    print trailer

form = cgi.FieldStorage()
if 'r' in form:
    if form['r'].value == 'n':
        h1 = "List of Authors who have declined"
        where = "WHERE reply = 'n'"
    else:
        h1 = "List of Authors who have agreed"
        where = "WHERE reply = 'y'"
else:
    h1= "List of Authors"
    where = ""

if 'd' in form:# and form['d'] == open('../adpass.txt').read().strip():
    details()
else:
    summary(h1, where)
