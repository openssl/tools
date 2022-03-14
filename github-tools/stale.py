#! /usr/bin/env python3
# requires python 3
#
# OpenSSL intersting PR stats on things that are stale
#
# note that we'd use pyGithub but we can't as it doesn't fully handle the timeline objects
# as of Feb 2020 and we might want to parse timeline if we want to ignore certain things
# from resetting 'updated' date
#
# mark@openssl.org Feb 2020
#
import requests
import json
from datetime import datetime, timezone
from optparse import OptionParser
from statistics import median
import collections
import csv

api_url = "https://api.github.com/repos/openssl/openssl"

def convertdate(date):
    return datetime.strptime(date.replace('Z',"+0000"), "%Y-%m-%dT%H:%M:%S%z")

def addcommenttopr(issue,comment):
    newcomment = {"body":comment}
    url = api_url + "/issues/" + str(issue) + "/comments"
    res = requests.post(url, data=json.dumps(newcomment), headers=headers)
    if (res.status_code != 201):
        print("Error adding comment", res.status_code, res.content)
    return

# Note: Closing an issue doesn't add a comment by itself

def closepr(issue,comment):
    newcomment = {"body":comment}
    url = api_url + "/issues/" + str(issue) + "/comments"
    res = requests.post(url, data=json.dumps(newcomment), headers=headers)
    if (res.status_code != 201):
        print("Error adding comment", res.status_code, res.content)    
    url = api_url + "/issues/" + str(issue)
    res = requests.patch(url, data=json.dumps({"state":"closed"}), headers=headers)
    if (res.status_code != 200):
        print("Error closing pr", res.status_code, res.content)
    return

# Get all the open pull requests, filtering by approval: done label

stale = collections.defaultdict(list)
now = datetime.now(timezone.utc)

def parsepr(pr, days):
    if (debug):
        print ("Getting timeline for ",pr['number'])
    url = api_url + "/issues/" + str(pr['number']) + "/timeline?per_page=100&page=1"
    res = requests.get(url, headers=headers)
    repos = res.json()
    while 'next' in res.links.keys():
        res = requests.get(res.links['next']['url'], headers=headers)
        repos.extend(res.json())

    comments = []
    commentsall = []
    readytomerge = 0
    reviewed_state = ""
    sha = ""

    for event in repos:
#        print (event['event'])
#        print (event)
#        print ()
        try:
            eventdate = ""
            if (event['event'] == "commented"):
                # we need to filter out any comments from OpenSSL Machine
                if "openssl-machine" in event['actor']['login']:
                    if (debug):
                        print("For stats ignoring automated comment by openssl-machine")
                    commentsall.append(convertdate(event["updated_at"]))
                else:
                    eventdate = event["updated_at"]
            elif (event['event'] == "committed"):
                sha = event["sha"]                
                eventdate = event["author"]["date"]
            elif (event['event'] == "labeled" or event['event'] == "unlabeled"):
                eventdate = event['created_at']
            elif (event['event'] == "reviewed"):
                reviewed_state = "reviewed:"+event['state'] # replace with last review
                eventdate = event['submitted_at']
            elif (event['event'] == "review_requested"):
                # If a review was requested after changes requested, remove changes requested label
                reviewed_state = "reviewed:review pending";
                eventdate = event['created_at']                
            if (eventdate != ""):
                comments.append(convertdate(eventdate))
#            print(reviewed_state)
        except:
            return (repos['message'])

    # We want to ignore any comments made by our automated machine when
    # looking if something is stale, but keep a note of when those comments
    # were made so we don't spam issues
        
    dayssincelastupdateall = int((now - max(comments+commentsall)).total_seconds() / (3600*24))
    dayssincelastupdate = int((now - max(comments)).total_seconds() / (3600*24))   
    if (dayssincelastupdate < days):
        if (debug):
            print("ignoring last event was",dayssincelastupdate,"days:",max(comments+commentsall))
        return

    labellist = []
    if 'labels' in pr:
        labellist=[str(x['name']) for x in pr['labels']]
    if 'milestone' in pr and pr['milestone']:
        labellist.append("milestone:"+pr['milestone']['title'])
    labellist.append(reviewed_state)
    labels = ", ".join(labellist)

    # Ignore anything "tagged" as work in progress, although we could do this earlier
    # do it here as we may wish, in the future, to still ping stale WIP items
    
    if ('title' in pr and 'WIP' in pr['title']):
        return
    
    data = {'pr':pr['number'],'days':dayssincelastupdate,'alldays':dayssincelastupdateall,'labels':labels}
    stale["all"].append(data)

    if debug:
        print (data)

    # The order of these matter, we drop out after the first one that
    # matches.  Try to guess which is the most important 'next action'
    # for example if something is for after 1.1.1 but is waiting for a CLA
    # then we've time to get the CLA later, it's deferred.  

    if (('Post 1.1.1' in labels) or
        ('milestone:Post 3.0.0' in labels)):
        stale["deferred after 3.0.0"].append(data)
        return
    if ('stalled: awaiting contributor response' in labels):
        stale["waiting for reporter"].append(data)
        return        
    if ('hold: need omc' in labels or 'approval: omc' in labels):
        stale["waiting for OMC"].append(data)
        return
    if ('hold: need otc' in labels or 'approval: otc' in labels):
        stale["waiting for OTC"].append(data)
        return
    if ('hold: cla' in labels):
        stale["cla required"].append(data)
        return
    if ('review pending' in labels):
        stale["waiting for review"].append(data)
        return
    if ('reviewed:changes_requested' in labels):
        stale["waiting for reporter"].append(data)
        return

    url = api_url + "/commits/" + sha + "/status"
    res = requests.get(url, headers=headers)
    if (res.status_code == 200):
        ci = res.json()
        if (ci['state'] != "success"): 
            stale["failed CI"].append(data)
            return

    stale["all other"].append(data)    
    return
    

def getpullrequests(days):
    url = api_url + "/pulls?per_page=100&page=1"  # defaults to open
    res = requests.get(url, headers=headers)
    repos = res.json()
    prs = []
    while 'next' in res.links.keys():
        res = requests.get(res.links['next']['url'], headers=headers)
        repos.extend(res.json())

    # In theory we can use the updated_at date here for filtering, but in practice
    # things reset it --- like for example when we added the CLA bot, also any
    # comments we make to ping the PR.  So we have to actually parse the timeline
    # for each event.  This is much slower but more accurate for our metrics and
    # we don't run this very often.
    
    # we can ignore anything with a created date less than the number of days we
    # care about though
    
    try:
        for pr in repos:
            dayssincecreated = int((now - convertdate(pr['created_at'])).total_seconds() / (3600*24))            
            if (dayssincecreated >= days):
                prs.append(pr)
    except:
        print("failed", repos['message'])
    return prs

# main

parser = OptionParser()
parser.add_option("-v","--debug",action="store_true",help="be noisy",dest="debug")
parser.add_option("-t","--token",help="file containing github authentication token for example 'token 18asdjada...'",dest="token")
parser.add_option("-d","--days",help="number of days for something to be stale",type=int, dest="days")
parser.add_option("-D","--closedays",help="number of days for something to be closed. Will commit and close issues even without --commit flag",type=int, dest="closedays")
parser.add_option("-c","--commit",action="store_true",help="actually add comments to issues",dest="commit")
parser.add_option("-o","--output",dest="output",help="write a csv file out")
parser.add_option("-p","--prs",dest="prs",help="instead of looking at all open prs just look at these comma separated ones")

(options, args) = parser.parse_args()
if (options.token):
    fp = open(options.token, "r")
    git_token = fp.readline().strip('\n')
    if not " " in git_token:
       git_token = "token "+git_token
else:
    print("error: you really need a token or you will hit the API limit in one run\n")
    parser.print_help()
    exit()
debug = options.debug
# since timeline is a preview feature we have to enable access to it with an accept header
headers = {
    "Accept": "application/vnd.github.mockingbird-preview",
    "Authorization": git_token
}
days = options.days or 31
if (options.output):
    outputfp = open(options.output,"a")
    outputcsv = csv.writer(outputfp)

prs = []
if (options.prs):
    for prn in (options.prs).split(","):
        pr = {}
        pr['number']=int(prn)
        prs.append(pr)

if (not prs):
    if debug:
        print("Getting list of open PRs not created within last",days,"days")
    prs = getpullrequests(days)
if debug:
    print("Open PRs we need to check", len(prs))

for pr in prs:
    parsepr(pr, days)

if ("waiting for OMC" in stale):
    for item in stale["waiting for OMC"]:
        if (item['alldays']>=days):
            comment = "This PR is in a state where it requires action by @openssl/omc but the last update was "+str(item['days'])+" days ago"
            print ("   ",item['pr'],comment)
            if (options.commit):
                addcommenttopr(item['pr'],comment)

if ("waiting for OTC" in stale):
    for item in stale["waiting for OTC"]:
        if (item['alldays']>=days):        
            comment = "This PR is in a state where it requires action by @openssl/otc but the last update was "+str(item['days'])+" days ago"
            print ("   ",item['pr'],comment)
            if (options.commit):
                addcommenttopr(item['pr'],comment)

if ("waiting for review" in stale):
    for item in stale["waiting for review"]:
        if (item['alldays']>=days):        
            comment = "This PR is in a state where it requires action by @openssl/committers but the last update was "+str(item['days'])+" days ago"
            print ("   ",item['pr'],comment)
            if (options.commit):
                addcommenttopr(item['pr'],comment)

if ("waiting for reporter" in stale):
    for item in stale["waiting for reporter"]:
        if (options.closedays and item['days']>=options.closedays):
            comment = "This PR has been closed.  It was waiting for the creator to make requested changes but it has not been updated for "+str(item['days'])+" days."
            print ("   ",item['pr'],comment)
            if (options.commit):
                closepr(item['pr'],comment)
        elif (item['alldays']>=days):        
            comment = "This PR is waiting for the creator to make requested changes but it has not been updated for "+str(item['days'])+" days.  If you have made changes or commented to the reviewer please make sure you re-request a review (see icon in the 'reviewers' section)."
            print ("   ",item['pr'],comment)
            if (options.commit):
                addcommenttopr(item['pr'],comment)                            

if ("cla required" in stale):
    for item in stale["cla required"]:
        if (options.closedays and item['days']>=options.closedays):
            comment = "This PR has been closed.  It was waiting for a CLA for "+str(item['days'])+" days."
            print ("   ",item['pr'],comment)
            if (options.commit):
                closepr(item['pr'],comment)            
        elif (item['alldays']>=days):
            comment = "This PR has the label 'hold: cla required' and is stale: it has not been updated in "+str(item['days'])+" days. Note that this PR may be automatically closed in the future if no CLA is provided.  For CLA help see https://www.openssl.org/policies/cla.html"
            print ("   ",item['pr'],comment)
            if (options.commit):
                addcommenttopr(item['pr'],comment)

                
for reason in stale:
    days = []
    for item in stale[reason]:
        days.append(item['days'])
        if options.output and reason !="all":
            outputcsv.writerow([now,reason,item['pr'],item['labels'],item['days']])
            
    print ("\n", reason," (", len(stale[reason]),"issues, median ",median(days)," days)\n"),
    if (reason == "all" or "deferred" in reason):
        print ("   list of prs suppressed")
    else:
        for item in stale[reason]:
            print ("   ",item['pr'],item['labels'],"days:"+str(item['days']))
