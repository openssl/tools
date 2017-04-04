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
    <h1>List of Authors</h1>
    <p><a href="/">Main page</a></p>

    <p>Names appear multiple times because of multiple email addresses.</p>
"""

trailer = """
    <a href="/">Main page</a>
  </body>
</html>
"""

def summary():
    print header
    q = "SELECT name, uid FROM users ORDER BY name"
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
    counts = {}
    for row in cursor:
        name,uid,reply,date_replied,comment = row
        if comment is None or comment is '':
            comment = "--"
        if date_replied == None:
            date_replied = ''
        counts[reply] = counts.get(reply, 0) + 1
        print ("<tr>"
                "<td><a href='lookup.py?uid=%d'>%s</td>"
                "<td>%s</td>"
                "<td>%s</td>"
                "<td>%s</td></tr>") % (uid,name,reply,date_replied,comment)
    print "</table>"
    print "<p>Counts by response:</p>"
    print "<table border='1' class='cw'>"
    print "<tr><th>Reply</th><th>Count</th></tr>"
    total = 0
    for k in counts:
        print "<tr><td>%s</td><td>%d</td></tr>" % (k, counts[k])
        total += counts[k]
    print "<tr><td>%s</td><td>%d</td></tr>" % ("Total", total)
    print "</table>"
    print trailer

form = cgi.FieldStorage()

dpass = open('../adpass.txt').read().strip()
if 'd' in form and form['d'].value == dpass:
    details()
else:
    summary()
