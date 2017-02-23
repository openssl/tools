#! /usr/bin/env python
'''Create a CSV file from RT output.  OBSOLETE

Parse the output an RT buglist:
	rt ls -f status,created,resolved 'id>1'
aggregate statistics per-week. Output a CSV file that shows, for
each month, the number of new bugs report, resolved, or rejected,
and the cumulative totals for each category.'''

import sys

weekly = 1
opened, resolved, rejected = {}, {}, {}
keys = []

months = {
    'Jan': '01', 'Feb': '02', 'Mar': '03',
    'Apr': '04', 'May': '05', 'Jun': '06',
    'Jul': '07', 'Aug': '08', 'Sep': '09',
    'Oct': '10', 'Nov': '11', 'Dec': '12',
    }

def parsedate(datestr):
    '''Parse a string like "Wed Apr 24 17:38:26 2002"
    into a key "2001-04" (year month week).'''
    fields = datestr.split(' ')
    if fields is None or len(fields) != 5:
        return "?"
    week = 0
    try:
        week = int(fields[2]) / 7
    except:
        week = 0
    week += 1
    if weekly:
        return '%s-%s-%d' % (fields[4], months.get(fields[1], "?"), week)
    else:
        return '%s-%s' % (fields[4], months.get(fields[1], "?"))

records = 0
for line in sys.stdin:
    line = line[:-1]
    fields = line.split('\t')
    if fields is None or len(fields) != 4 or fields[0] == 'id':
        continue
    records += 1
    key = parsedate(fields[2])
    if key not in keys:
        keys.append(key)
    if not opened.has_key(key):
        opened[key] = 0;
    opened[key] += 1
    if fields[3] == 'Not set':
        continue
    key = parsedate(fields[3])
    if key not in keys:
        keys.append(key)
    if not resolved.has_key(key):
        resolved[key] = 0;
    if not rejected.has_key(key):
        rejected[key] = 0;
    if fields[1] == 'resolved':
        resolved[key] += 1
    else:
        rejected[key] += 1

# Open, resolved, rejected cumulative totals
ocum, rcum, xcum = 0, 0, 0
print 'date,opened,tot-opened,resolved,tot-res,rejected,tot-rej,tot-closed,num-open'
keys.sort()
for k in keys:
    o = opened.get(k, 0)
    ocum += o
    r = resolved.get(k, 0)
    rcum += r
    x = rejected.get(k, 0)
    xcum += x
    print "%s, %d, %d, %d, %d, %d, %d, %d,  %d" % \
        (k, o, ocum, r, rcum, x, xcum, rcum+xcum, ocum - rcum - xcum)
