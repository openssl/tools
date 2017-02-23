
GITURL	= https://api.github.com/repos/openssl/openssl
WWWREPO = ../www.openssl.org
SRCREPO = ../gitlab

SINCE	?= $(shell date +%Y-%m)
#SINCE	= 2016-01
SINCE2	=$(subst -,,$(SINCE))01

VULN	= $(WWWREPO)/news/vulnerabilities.xml

REFRESH	= bugs.full pulls issues

ALL	= cve.txt releases.txt \
	  bugs.csv \
	  team.full team.counts \
	  pulls.csv issues.csv

all:	$(ALL)

.PHONY: refresh
refresh:
	@rm -rf $(REFRESH)
	$(MAKE) $(REFRESH)

.PHONY: report
report:
	./makereport $(SINCE)

check:
	test -d $(WWWREPO) -o -d $(WWWREPO)/.git || exit 1
	test -f $(VULN) || exit 1
	test -f $(VULN) || exit 1
	test -d $(SRCREPO) -o -d $(SRCREPO)/.git || exit 1

.PHONY: clean
clean:
	rm -f $(ALL)
	rm -rf issues pulls


cve.txt: cve.xsl $(VULN)
	@rm -f $@
	( cd $(WWWREPO) ; git pull )
	xsltproc cve.xsl $(VULN) | sed -e 's/^  //' -e '/^$$/d' | \
	    awk '$$1 >= $(SINCE2) { print; }' >$@

releases.txt: cve.txt
	@rm -f $@
	awk -F, '{print $$4; print $$5; print $$6; }' <cve.txt | \
	    sort -u | sed -e 1d -e 's/ //' | sort -r >$@


bugs.full:
	@rm -f $@
	ssh rt.openssl.org 'rt ls -f status,created,resolved "id>1"' >$@

bugs.csv: bugs.full bugs2csv.py
	@rm -f $@
	python bugs2csv.py $(SINCE2) <bugs.full >$@

.PHONY: team.full
team.full:
	@rm -f $@
	( cd $(SRCREPO) && git log '--since=$(SINCE)-01' '--format=%ce' ) | \
	sed -e s/kurt@roeckx.be/kurt@openssl.org/ \
	 -e s/openssl-users@dukhovni.org/viktor@openssl.org/ \
	 -e s/ben@links.org/ben@openssl.org/ \
	 -e s/rsalz@akamai.com/rsalz@openssl.org/ \
	 -e s/richard@levitte.org/levitte@openssl.org/ \
	 | grep @openssl.org | sort >$@

team.counts: team.full
	@rm -f $@
	uniq -c team.full | sort -n >$@

.PHONY: pulls.csv
pulls.csv:
	@rm -f $@
	python stats2csv.py pulls $(SINCE2) >$@

.PHONY: issues.csv
issues.csv:
	@rm -f $@
	python stats2csv.py issues $(SINCE2) >$@

pulls:
	@rm -f $@
	./ghstats pulls '$(GITURL)'

issues:
	@rm -f $@
	./ghstats issues '$(GITURL)'
