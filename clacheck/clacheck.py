#! /usr/bin/env python
"""GitHub web hook.  Take PullRequest messages, and check the authors
for the CLA.

Look for <EDIT> comments for pointers on where to customize
"""

import cgi, cgitb
import json, urllib, os, re, sys, httplib

cgitb.enable()

env = os.environ
textplain = "Content-type: text/plain\n\n"
what = env.get('HTTP_X_GITHUB_EVENT', 'ping')
From_re = re.compile("^From:.*<(.*)>")
Trivial_re = re.compile("^\s*CLA\s*:\s*TRIVIAL", re.IGNORECASE)
URLpattern_re = re.compile("https?://([^/]*)/(.*)")
CLAFILE = "/var/cache/openssl/checkouts/omc/cladb.txt" #<EDIT>

# states
SUCCESS = 'success'             # CLA is fine and no 'CLA: trivial' in sight
FAILURE = 'failure'             # No CLA or 'CLA: trivial' found

CLA_LABEL = 'hold: cla required'
TRIVIAL_LABEL = 'cla: trivial'

null_actions = (
        'assigned', 'unassigned', 'labeled', 'unlabeled', 'closed',
        'review_requested', 'review_request_removed',
        )

#<EDIT> target_url value
statusbody = """
{
    "state": "%(state)s",
    "target_url": "https://www.openssl.org/policies/cla.html",
    "description": "%(description)s",
    "context": "cla-check"
}
"""

def url_split(url):
    m = URLpattern_re.match(url)
    return (m.group(1), '/' + m.group(2))

# Global connection data, all set up by start_conn
token = ""
conn = None

def start_conn(pr):
    host,url = url_split(pr['_links']['statuses']['href'])

    global conn
    global token
    if conn != None:
        return                  # Connection already opened

    token = open('../ghpass.txt').read().strip() #<EDIT> password file
    conn = httplib.HTTPSConnection(host)

def update_conn(pr, cmd, url, data):
    headers = {
            'Authorization': 'token ' + token,
            'User-Agent': 'openssl-machine',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            }
    conn.request(cmd, url, data, headers)
    return conn.getresponse().read()

def update_labels(pr, labels):
    start_conn(pr)

    host,url = url_split(pr['issue_url'])

    # remove all our known labels if none are given
    if len(labels) == 0:
        for label in [ CLA_LABEL, TRIVIAL_LABEL ]:
            print 'Delete label', label
            reply = update_conn('DELETE',
                                url + '/labels/' + urllib.quote(label),
                                None)
            print "--\n", reply

    # add any label that is given
    if len(labels) > 0:
        print 'Add labels', ', '.join(labels)
        formatted_labels = [ '"{}"'.format(label) for label in labels ]
        reply = update_conn('POST',
                            url + '/labels',
                            '[ {} ]'.format(','.join(formatted_labels)))
        print "--\n", reply

def update_status(pr, state, description):
    start_conn(pr)

    d = { 'state': state, 'description': description }

    host,url = url_split(pr['_links']['statuses']['href'])
    print textplain, "CLA check", state, description
    update_conn(pr, 'POST', url, statusbody % d)
    host,url = url_split(pr['issue_url'])

def have_cla(name):
    """Is |name| in the cladb?"""
    for line in open(CLAFILE):
        line = line.strip()
        if not line or line[0] == '#':
            continue
        n = line.split()
        if len(n) and n[0] == name.lower():
            return 1
    return 0

def process():
    if what != 'pull_request':
        print textplain, "Request", what
        return
    data = json.loads(sys.stdin.read())
    action = data.get('action', None)
    if action is None or action in null_actions:
        print textplain, "No-op action", action
        return
    pr = data.get('pull_request', None)
    if pr is None:
        print textplain, "PR data missing"
        return
    patch_url = pr.get('patch_url', None)
    if patch_url is None:
        print textplain, "patch_url missing"
        return

    # Read through the patch set, which is formatted like 'git format-patch'
    missing = {}                # collects names for missing CLAs
    tmpmissing = {}             # collects names for missing CLAs in one commit
    any_trivial = 0

    for line in urllib.urlopen(patch_url):
        # From: marks the beginning of a commit well enough
        m = From_re.match(line)
        if m:
            # Update missing with the names from the previous commit
            missing.update(tmpmissing);
            tmpmissing = {}

            if not have_cla(m.group(1)):
                tmpmissing[m.group(1)] = 1

        # CLA: trivial clears the current collection of missing CLAs
        m = Trivial_re.match(line)
        if m:
            tmpmissing = {}
            # If there was ANY CLA:trivial, we label it as such
            any_trivial = 1

    # Update missing with the names from the last commit
    missing.update(tmpmissing);

    # Clear all known labels
    update_labels(pr, [])

    # Set status
    if len(missing) == 0:
        update_status(pr, SUCCESS, 'CLA on file or all trivial commits')
    else:
        update_status(pr, FAILURE, "CLA missing: " + str(missing.keys()))
        # add the [hold: cla needed] label
        update_labels(pr, [ CLA_LABEL ])

    # add the [cla: trivial] label if any trivial commit was found
    if any_trivial:
        update_labels(pr, [ TRIVIAL_LABEL ])

process()
