#! /usr/bin/env python

import datetime, glob, json, sys

dtparse = datetime.datetime.strptime

def parse(d):
    return dtparse(d, '%Y%m%d')

files = glob.glob(sys.argv[1]+ "/*.js")
files.sort()
when = sys.argv[2]

print "open, closed, duration, #, state, user"
for f in files:
    items = json.load(open(f))
    for i in items:
        created = i["created_at"][:10].replace('-', '')
        closed = i["closed_at"];
        if closed is None:
            closed = '-'
            duration = 0
        else:
            closed = closed[:10].replace('-', '')
            duration = (parse(closed) - parse(created)).days
        if created >= when:
            print "%s, %s, %d, %s, %s, %s" % \
                ( created, closed, duration, i["number"], i["state"], i["user"]["login"])
