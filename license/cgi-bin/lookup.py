#! /usr/bin/env python

import cgi
import cgitb
import mysql.connector

cgitb.enable()

# Open links in newpage?
target = 'target="_blank"'
where = ' (commits open in a new window)'

urlbase = 'https://github.com/openssl/openssl/commit/'

dbconfig = {
        'user': 'licensereader',
        'password': open('../ropass.txt').read().strip(),
        'database': 'license'
        }

print """Content-Type: text/html

<html>
  <head>
    <title>Search results - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>Search results</h1>

    <p><a href="/">Main page</a></p>

    <p>"""

def show_log(email):
    """Ouput HTML for all commits from |email|. Returns the uid."""
    conn = mysql.connector.connect(**dbconfig)
    cursor = conn.cursor()
    q = "SELECT uid, reply FROM users WHERE email = %s"
    cursor.execute(q, (email,))
    row = cursor.fetchone()
    if not row:
        print "No commits by %s: No such developer</p>" % (email,)
        return None
    uid, reply = row
    q = "SELECT count(cid) FROM log WHERE uid = %s"
    cursor.execute(q, (uid,))
    row = cursor.fetchone()
    if not row or not row[0]:
        print "No commits by", email
        return None
    count = row[0]
    q = ("SELECT commit, date, descrip FROM commits"
         " LEFT JOIN log ON commits.cid = log.cid"
         " WHERE uid = %s ORDER BY date, commit")
    cursor.execute(q, (uid,))
    print "Found %d commits by %s%s:\n</p>" % (count, email, where)
    print "<p class='cw'>"
    print "<table>"
    for row in cursor:
        commit, cdate, descrip = row
        print '<tr><td><a href="%s%s" %s>%s</a>&nbsp;</td>' % \
            (urlbase, commit, target, commit)
        print '<td>%s&nbsp;</td><td>%s&nbsp;</td></tr>' % (cdate, descrip)
    print "</table></p>"
    return uid

trailer = """
    <a href="/">Main page</a></p>
  </body>
</html>
"""

form = cgi.FieldStorage()
if 'onepage' in form:
    where = target = ''
if 'email' not in form:
    print "No email specified\n", "<p>\n", trailer
    raise SystemExit

print '<p>'
uid = show_log(form['email'].value.replace('<', '&lt;'))
if uid != None:
    print '<a href="/cgi-bin/send-email.py?uid=%s">' \
            'Send agreement email</a><br>' % (uid,)

print trailer
