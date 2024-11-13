# HOW TO HANDLE A SECURITY ISSUE

Security issues are handled differently from normal bug/feature issues.

In summary, they must:

-   Get an issue raised in the [private otc/security repository]
-   Receive a severity classification, see our [Security Policy]
-   Receive a CVE ID
-   Receive a fix (collected as a PR in the [private openssl/security repository])
-   Receive a draft advisory (committed to the [private otc/security repository])
-   Become part of a release

Below is a more detailed guide for this process.

## Sources of truth

-   <openssl-security@openssl.org>

    This is the primary contact point that people are encouraged to send a
    message to, to say "we found a bug" that affects security.

    This list is also the recipient of automated security related testing
    logs.  More on those in the sub-section below.

-   Issues in the [public openssl/openssl repository]

    If someone files an issue here, that is discovered to be a
    security issue, redirect the issue author (the reporter) to
    <openssl-security@openssl.org>, if it's possible to reach them.

These sources of truth must be watched on a regular and frequent basis.

### Automated security related testing logs

We receive automated security related testing logs to
<openssl-security@openssl.org> from the following channels:

-   VINCE (From: <cert+donotreply@cert.org>)

    This is currently a fairly low intensity channel.
    Mark usually looks at this so far, and notifies us
    if there's something to look at.

-   oss-fuzz (Reply-To: <oss-fuzz@monorail-prod.appspotmail.com>)

    This is a high intensity channel, which includes two fuzz testing
    projects of importance to us:

    -   cryptofuzz

        This is Guido Vranken's initiative, and is made to test that
        OpenSSL, diverse forks of it and other crypto libraries don't
        diverge in their outputs.  Guido alerts us if anything important
        comes up.

        Issues from this project are identified by subjects that include
        `cryptofuzz:`, for example:

        ```
        Subject: [openssl-security] Issue 54290 in oss-fuzz: cryptofuzz: Fuzzing build failure
        ```

    -   openssl

        This is a setup that runs our own fuzzers.

        Issues from this project are identified by subjects that include
        `openssl:`, for example:

        ```
        Subject: [openssl-security] Issue 53789 in oss-fuzz: openssl:cms_111: Null-dereference WRITE with empty stacktrace
        ```

## Initial actions (before release is planned)

### Dealing with non-issues or issues that we don't consider security

*To be done by anyone that wants to pitch in, the security manager being a
fallback*

Every so often, we receive reports on <openssl-security@openssl.org> that we
obviously don't consider issues, or at least security related issues.  For
those, just report to the reporter that we do not consider this a security
issue.

In the [private omc/data repository], there's a standard response in the file
`standard-responses/not-security-vulnerability`, which can be used as is, or
as an inspiration.  It also specifies some well known reports that we don't
consider security issues.

### Record new security issues in the [private otc/security repository]

*To be done by anyone that wants to pitch in, the security manager being a
fallback*

Create a new issue in the [private otc/security repository], and copy
the issue text there.  Above that text, add references to the original,
separated from the text with a horizontal line (in markdown, that's
five dashes or more on a line, separated from the rest with an empty
line above and below):

-   If the original came in through <openssl-security@openssl.org>, include
    at least the following e-mail fields:

    -   From:
    -   Subject:
    -   Date:
    -   Message-ID:

    Example:

    > ``` text
    > From: John Citizen <john.citizen@example.com>
    > Subject: [openssl-security] Timing oracle in MDC2
    > Date: Tue, 29 Feb 2000 10:59:59 +0000
    > Message-ID: <950124.162336@example.com>
    >
    > -----
    >
    > TEXT
    > ```

-   If the original came in the [public openssl/openssl repository], add the
    following:

    -   Original issue: <https://github.com/openssl/openssl/issue/xxxxx>
    -   Date: (date from the issue description)

    Example:

    > ``` text
    > Original issue: https://github.com/openssl/openssl/issue/12345
    > Date: 2000-02-29
    >
    > -----
    >
    > TEXT
    > ```

Set the following labels on that issue:

-   Severity needed
-   CVE ID needed

Acknowledge back to the reporter and on <openssl-security@openssl.org> that
this issue has been received and is on record.

### Investigate the issue

*To be done by anyone that wants to pitch in, or someone that the OTC
assigns during the next following OTC meeting*

Investigating the issue includes figuring out:

-   if it actually is a security issue
-   which releases and release versions it affects
-   the severity classification

Report back the conclusions of the investigation to the reporter and on
<openssl-security@openssl.org>, and is often confirmed through an email
exchange or on the next OTC meeting.

### Assign a severity classification (or just fix the issue)

*To be done by the person that investigated the issue*

Doing any of this requires confirmation from other people on
<openssl-security@openssl.org> or from the OTC.

If the issue is determined to not be a security issue, but is still worthy
of a fix:

-   raise an issue in the [public openssl/openssl repository], unless the
    original issue was already raised there.
-   close the issue in the [private otc/security repository].

If the issue was confirmed to be a security issue, modify the labels on the
issue in the [private otc/security repository]:

-   drop "Severity needed"
-   add "CVE ID needed"
-   add "severity: xxxxx", which one depends on the investigation conclusions.
-   add the versions affected.

### Assign a CVE ID (see [private cvepool.md])

This requires credentials.

Report the CVE ID back to the reporter and on <openssl-security@openssl.org>

Modify the title of the issue raised in the [private otc/security repository] to
start with the CVE ID (i.e. `CVE-YYYY-NNNN`).

Modify the labels on the issue in the [private otc/security repository]:

-   drop "CVE ID needed"

### Write an early advisory text

*To be done by the investigator (default), or anyone that wants to pitch in*

NOTE: The reporter may have written something good enough in their report to
serve as inspiration (it may even be good enough to copy verbatim).

It's ***strongly** recommended* to put together an early advisory text,
before publishing the fixes (as part of a release, or for Low severity
issues, as individual PRs), or even before planning to publish them.  In
essence, as early as possible.

Since early advisory texts are intended to be made this early, they are tied
to the CVE ID, and are committed (after the usual process of submitting a
PR, getting it approved, and merging it) to the
[private otc/security repository] as`draft-advisories/CVE-YYYY-NNNN.txt`.

The advisory text should be written according to the template found in
`draft-advisories/CVE-template.txt`, replacing any word in braces (`{` and
`}`) with appropriate text, and otherwise edited to make sense.

Do note that some of the lines in `draft-advisories/CVE-template.txt` may
need to be repeated, such as information on affected series, see this
example:

```
OpenSSL 1.0.2 users should upgrade to 1.0.2a (premium support customers only)
OpenSSL 1.1.1 users should upgrade to 1.1.1a
OpenSSL 3.0 users should upgrade to 3.0.1
```

If you need help, ask for it.

*NOTE: It's possible to write the advisory text late, as part of releases or
publishing the security advisory.  We **strongly** recommend against that,
though, among others because release and publishing time often a stressful
moment.  In the end, it's your judgement call.*

### Create the fix (Low severity issue)

*Creating the fix is to be done by the original reporter, or the investigator,
or anyone that wants to pitch in, or someone that the OTC assigns during the
next following OTC meeting*

Low severity issues are usually treated like any public bug fix on [public
openssl/openssl repository], except for creating (described in [Write a
security advisory text] below) and publishing (described in [Publish the
security advisories] below) the security advisory.

An exception can be made if a release is imminent.  In that case, it can be
handled as part of the release, the same way as the higher level issue fixes.

### Create and collect the fix (Moderate / High / Critical severity issue)

*Creating the fix is to be done by the original reporter, or the investigator,
or anyone that wants to pitch in, or someone that the OTC assigns during the
next following OTC meeting*

*Collecting the fix is to be done by the investigator, anyone who wants to
pitch in, or someone that the OTC assigns during the next OTC meeting*

Fixes for Moderate / High / Critical severity issues are collected as PRs --
usually one per issue.  For public releases, they must be submitted to the
[private openssl/security repository], while for premium releases, they must be
submitted to the [private openssl/premium repository].

Note that it may be necessary to get the [private openssl/security repository]
in sync with the [public openssl/openssl repository] before submitting a PR.
We don't automate that because the [private openssl/security repository]
serves as a staging repository for security releases, so uncontrolled
synchronisations may be disruptive.

Make sure that each PR description includes reference to the issue; something
like this on a standalone line, with `nnn` replaced with the issue number:

```
Fixes otc/security#nnn
```

Make sure that the commit that contains the actual fix has the CVE ID in its
commit message.  A PR may contain other commits, e.g. for adding test cases,
or doing additional hardening inspired by the original problem.

## Making a release (Moderate / High / Critical severity issues)

Most of the release mechanics are found in [HOWTO-make-a-release.md] and
will not be repeated here.

For premium releases, there's nothing additional to do, simply work off the
[private openssl/premium repository] as usual.

For public releases, some extra preparation is necessary, since the security
fixes are staged in the [private openssl/security repository] but will end
up in the [private openssl/openssl repository].

The recommended preparation is this:

1.  Make sure that all the applicable (non-security) PRs on the [public
    openssl/openssl repository] have been merged

2.  Make sure you have appropriate remotes registered (you can do without,
    but that's a bit more complicated, so it's *recommended* to have remotes
    registered):

    ``` console
    $ cd {your-openssl-work-directory}
    $ git remote add security git@github.openssl.org:openssl/security.git
    $ git remote add openssl git@github.openssl.org:openssl/openssl.git
    ```

    You may already have these or similar remote names registered for these,
    which is perfectly ok, just remember to use them instead of `security`
    or `openssl` when following the rest of the instructions.

3.  Make sure that the applicable release branches in the
    [openssl/security repository] are in sync with the
    [private openssl/openssl repository].
    Here's an example how to do this (using the remote names from above:

    ``` console
    $ cd {your-openssl-work-directory}
    $ git fetch openssl
    ```

    Then, for each release branch:

    ``` console
    $ git push security openssl/{branch}:{branch}
    ```

4.  Make sure that all the applicable (security) PRs on the
    [private openssl/security repository] are merged.

5.  Update the branches in your local clone:

    ``` console
    $ git fetch security
    $ git checkout {branch}
    $ git rebase security/{branch}
    ```

At this point, your local repository should be properly set up to perform
the release following the instructions in [HOWTO-make-a-release.md].  When
publishing, push to the [private openssl/openssl repository], and you
may also want to push to the [private openssl/security repository]
for good measure.

### Planning for a release

Depending on the severity of the issue, update releases may need to be
planned and carried out promptly.  This is determined by the highest
severity issue currently raised:

-   For Moderate severity issues, plan to merge the fixes as part of the
    next update release.

-   For High / Critical severity issues, plan for an update release as
    immediately as possible (within 4 weeks after the issue have been
    raised)

For the rest of the description, it's assumed that the plan for a release
includes a date when that release is done.

### Write a security advisory text

Security advisory texts are usually associated with a release.  For Low
security issues, they are usually associated with the PR that fixes the
issue.

In all cases, a security advisory must be written.  This is a text file,
initially saved as `draft-advisories/secadv_{YYYYMMDD}.txt` in the
[private otc/security repository], where `{YYYYMMDD}` is the release date,
or for a Low security issue, the date the fixing PR is merged.

This file shall be formatted according to following template:

```
OpenSSL Security Advisory [{DATE}]
==================================

{EARLY-ADVISORY-TEXTS}

References
==========

URL for this Security Advisory:
https://www.openssl.org/news/secadv/{YYYYMMDD}.txt

Note: the online version of the advisory may be updated with additional details
over time.

For details of OpenSSL severity classifications please see:
https://www.openssl.org/policies/general/security-policy.html
```

Where:

-   `{DATE}` must be replaced with the verbose date.
    For example, "29 February 2000"

-   `{EARLY-ADVISORY-TEXTS}` is replaced with the collection of early
    advisory texts (the `draft-advisories/CVE-{YYYY}-{NNNN}.txt` that are
    discussed in [Write an early advisory text] above) for which fixes are
    included in this release.  *This must include the early advisory texts
    for Low severity issues for which the fixes have already been pushed to
    the release branch*

    It's *recommended* to have them sorted by severity classification (order
    Critical to Low), and by date within each classification. 

-   `{YYYYMMDD}` is replaced with the date in numeric form, for example
    "20000229" for 29 February 2000.

If an issue for which a fix is included in this release doesn't have an
associated `draft-advisories/CVE-YYYY-NNNN.txt`, now's the time to write
one!

### Create a GitHub Security Advisory

Associated with a release, there must also be a [GitHub Security Advisory],
which is a protected fork of the [public openssl/openssl repository] made
for collaborating around a specific security related release.

The steps to follow are:

-   create a draft [GitHub Security Advisory] (from now on called GHSA) for
    the [public openssl/openssl repository]
    *(to be done with someone with admin rights)*

-   Populate the GHSA description with the security advisory text for the
    release that's talked about in the previous section.

-   Populate it with the appropriate fixes (copies of the PRs found in the
    [private openssl/security repository]).

-   Make "otc" and "openssl owners" and anyone else that's on
    <openssl-security@openssl.org> collaborators.

-   If the reporter has a github ID, invite them as a collaborator as well.

-   Report back the link to this security advisory to the reporter and on
    <openssl-security@openssl.org>

The GHSA fork is used to communicate changes and changes to dates etc.
Monitor this conversation to get feedback on the patches, testing, and
advisory.  Update the PRs in the [private openssl/security repository]
and advisory texts in `draft-advisories` in the
[private otc/security repository] as needed.

Example security advisory:
<https://github.com/openssl/openssl/security/advisories/GHSA-4hx9-frfq-wf7r>

### Pre-notification

Two weeks before the release date pre-notify our extended support customers and
pre-notification vendors that there will be an update release that includes
security related fixes.

-   The pre-notification to OS distro vendors goes to
    <distros@vs.openwall.org> and a small selection of friends, see the
    example in [Special handling of vendors] below.

-   The pre-notification to our extended support customers goes to
    <extended-support-announce@openssl.org>, see [Special handling of support
    customers] below.

A week before the release date announce the release to our support customers,
the public, and the oss-security list.

-   The announcement to our support customers goes to
    <support-announce@openssl.org>, see [Special handling of support
    customers] below.

-   The public announcement goes to <openssl-announce@openssl.org>,
    <openssl-users@openssl.org> and <openssl-project@openssl.org>
    [Example](https://mta.openssl.org/pipermail/openssl-announce/2020-April/000170.html)

-   If the releases will contain security fixes then we also send an
    announcement to the <oss-security@lists.openwall.com> list

### Special handling of support customers

Using `securityissues/premiumemail-template.txt` found in the [omc/data
repository] as a template, write a pre-notification email text for our
support customers, and save it in that same directory (`securityissues/` in
the [private omc/data repository]).

The template includes relevant email header fields, and should be preserved
as is in the saved email file.

This email must include the advisory text, an end of embargo date, and ask
who wants to be sent the patch that fixes the issues.  Record those who want
to receive the patch in the email file mentioned above (in `securityissues/`).

See previous files in `securityissues/` there as examples.

After having sent the email, <osf-contact@openssl.org> must be monitored for
responses from those who want to receive the patch; they must be recorded in
the `prenotified-customers.md` file in the [private omc/data repository].

### Special handling of vendors

Vendors plus a small selection of friends are handled a bit specially, as
they can opt in for collaborating with us on a per update release basis.

To handle this, write a pre-notification email text for them, using
`securityissues/vendoremail-template.txt` found in the [private omc/data repository]
as a template, and save it in that same directory (`securityissues/` in the
[private omc/data repository]).

Example (note the `[vs]` in the subject line, this is essential):

> ```
> To: distros@vs.openwall.org
> Bcc: libressl-security@openbsd.org, David Benjamin <davidben@google.com>,
>      OpenSSL Security <openssl-security@openssl.org>
> Subject: [vs] Embargoed OpenSSL issue
>
> On 29th February 2000 we'll be publishing an update to OpenSSL 1.1.1 that
> fixes a single "High" [www.openssl.org/policies/secpolicy.html] severity
> issue. This issue does not affect OpenSSL versions before 1.1.1d.
>
> As before we will be happy to give the draft advisory and patch to distros
> that include OpenSSL in the hope you can test it and provide us feedback
> prior to release.
>
> For prenotifications we are using a temporary private github fork
> [https://help.github.com/en/github/managing-security-vulnerabilities/collaborating-in-a-temporary-private-fork-to-resolve-a-security-vulnerability]
>
> If you'd like access to it please reply to me personally with your
> organisation name and github user name (or a couple of names) and state
> that you'll abide by the embargo [1]. I'll reply with instructions later
> today.
>
> Note: We will be notifying the public later today that we plan such a
> release but without any details.
>
> Regards, {sender's name}
>
> [1] Basically you'll keep this to within your organisation for the purpose
>     of building and testing fixes for this issue and you will not share it
>     with clients, customers or anyone else prior to you seeing the actual
>     advisory be public at openssl.org.
> ```

For each vendor or friend that replies and accepts:

-   Update the [private prenotified vendors log].
-   Invite them to the GHSA and make them a contributor.  They will be
    notified of this by GitHub.

NOTE: we make them go through this *every time*, as people may move position
and it reminds them of our embargo etc.
*(Sometimes we've skipped this step and just added the ones who asked last
time, it's okay if it's an emergency or we're short of time, just don't do
it every time.)*

## Post-release actions

Note that this includes publishing Low severity CVEs previous to a release.

### Publish the security advisories

*(For Low severity issues, this includes the initial publication of its
security advisory, which is not part of a release process)*

-   Prepare the security advisory text:

    -   Copy `draft-advisories/secadv_{YYYYMMDD}.txt` from the [otc/security
        repository] to `secadv/{YYYYMMDD}.txt` in a checkout of the [omc/data
        repository].
    -   Add a line in `newsflash.txt` in the [private omc/data repository],
        looking approximately like this:

        ```
        {DD-MMM-YYYY}: <a href="/news/secadv/{YYYYMMDD}.txt">Security Advisory</a>: one low severity fix</a>
        ```

        Where:

        -   `{DD-MMM-YYYY}` is the date in slightly verbose form, for
            example "29-Feb-2000".
        -   `{YYYYMMDD}` is the date in numeric form, for example 20002029
            for 29 February 2000.

-   Prepare the CVE advisories:

    -   Use the text from applicable `draft-advisories/CVE-YYYY-NNNN.txt`
        files, use vulnogram as described in [private cvepool.md] to create
        corresponding JSON files, and save them as
        `vulnerabilities-json/CVE-YYYY-NNNN.json` in a checkout of the
        [private omc/data repository].

    -   For Low severity issues *that end up in a release*, update the
        already existing `vulnerabilities-json/CVE-YYYY-NNNN.json` by
        changing the "lessThan" value `{major}.{minor}.{patch}-dev` to
        `{major}.{minor}.{patch}`.

Submit a PR containing all the added and changed files
(all new CVE files in `secadv/` and in `vulnerabilities-json/` and the
updated `newsflash.txt`), wait for approval and merge.  Our automation will
do the rest of the work to update out web site.

Finish by publishing all the applicable
`vulnerabilities-json/CVE-YYYY-NNNN.json` as instructed in [private cvepool.md].

[public openssl/openssl repository]: https://github.com/openssl/openssl
[Security Policy]: https://www.openssl.org/policies/general/security-policy.html
[GitHub Security Advisory]: https://docs.github.com/en/code-security/security-advisories/repository-security-advisories/about-repository-security-advisories
[HOWTO-make-a-release.md]: ./HOWTO-make-a-release.md

[Write an early advisory text]: #write-an-early-advisory-text
[Write a security advisory text]: #write-a-security-advisory-text
[Publish the security advisories]: #publish-the-security-advisories
[Special handling of support customers]: #special-handling-of-support-customers
[Special handling of vendors]: #special-handling-of-vendors

[private otc/security repository]: https://github.openssl.org/otc/security
[private openssl/security repository]: https://github.com/openssl/security
[private openssl/premium repository]: https://github.openssl.org/openssl/premium
[private openssl/openssl repository]: https://github.openssl.org/openssl/openssl
[private omc/data repository]: https://github.openssl.org/omc/data
[private cvepool.md]: https://github.openssl.org/otc/security/cvepool.md
[private prenotified vendors log]: https://github.openssl.org/otc/security/prenotified-vendors.md
