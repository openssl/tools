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
    <title>Author Search results - OpenSSL License Change Agreement</title>
    <link rel="stylesheet" type="text/css" href="/style.css">
  </head>
  <body>
    <h1>Author Search results</h1>
    <p><a href="/">Main page</a></p>
    <p>"""

def show_log(uid, email):
    """Ouput HTML for all commits from  |uid| or |email|.  If uid is None
    then look up email.  Returns the uid."""
    conn = mysql.connector.connect(**dbconfig)
    cursor = conn.cursor()
    if uid:
        q = "SELECT email, reply FROM users WHERE uid = %s"
        cursor.execute(q, (uid,))
        row = cursor.fetchone()
        if not row:
            print "No commits by id %s: No such developer</p>" % (uid,)
            return None
        email, reply = row
    else:
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

form = cgi.FieldStorage()
if 'text' in form:
    pattern = '%' + form['text'].value + '%'
    conn = mysql.connector.connect(**dbconfig)
    cursor = conn.cursor()
    q = ("SELECT name, uid FROM users WHERE"
        " name LIKE %s OR email LIKE %s ORDER BY name")
    cursor.execute(q, (pattern,pattern))

    print "<p class='cw'>"
    for row in cursor:
        name, uid = row
        name = name.encode('ascii', errors='xmlcharrefreplace')
        print '<a href="lookup.py?uid=%d">%s</a><br>' % (uid,name)
        #print '<a href="lookup.py?uid=%d">' % (uid,) + name + '</a><br>'
    print "</p>"
else:
    print "No text specified"

print '<p>'

print """
    <a href="/">Main page</a></p>
  </body>
</html>
"""
