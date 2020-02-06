Do we have any open openssl PR requests that have the label
"approval: done" that are over 24 hours old?  If so if there
have been no other comments added since then we can automatically
move them to "approval: ready to merge"

You need a token to make label changes and to ensure you don't
hit rate limiting if you just want a dry run.  Get one from
https://github.com/settings/tokens/new select 'repo' only
then put it in token.txt (prefix with the string "token ", i.e.
echo "token 12903413aaaaaa" > token.txt

to see what it would do:

python github-approve-label-workflow --debug --token token.txt

or to also actually change any labels

python github-approve-label-workflow --debug --token token.txt --commit

Requires Python 3
