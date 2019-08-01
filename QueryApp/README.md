QueryApp
========

A web app to answer OpenSSL queries, primarely to serve anything that
uses the OpenSSL::Query modules.

This includes an OpenSSL::Query implementation that looks directly at
the databases, OpenSSL::Query::DB.

This also includes a query.psgi that is used to serve the data, and a
couple of dispatchers for CGI and FCGI.  These are designed to be used
directly in the checkout, but will work if copied elsewhere as well,
as long as the OpenSSL::Query::DB module is installed.

REST API
--------

RESTAPI.txt documents the details of the REST API provided by QueryApp.

Requirements
------------

OpenSSL::Query requires the following modules to build:

- Module::Install		(debian package libmodule-install-perl)

OpenSSL::Query requires these extra modules to run:

- YAML::XS			(debian package libyaml-libyaml-perl)
- Moo				(debian package libmoo-perl)
- Dancer2			(debian package libdancer2-perl)
- Plack				(debian package libplack-perl)
- URI::Encode			(debian package liburi-encode-perl)
- Clone				(debian package libclone-perl)
- OpenSSL::Query		(from ../OpenSSL-Query)

Any other module OpenSSL::Query depends on should be part of core
perl.

Installation
------------

    $ perl Makefile.PL
    $ make
    $ make install

Local installation
------------

For a local installation, you might want to consider using local::lib
(debian package liblocal-lib-perl).  In that case, running Makefile.PL
is slightly different:

    $ perl -Mlocal::lib Makefile.PL

Other than that, follow the instructions in "Installation" above.

The local installation method works best if the `PERL5LIB` environment variable
(among others) is set correctly in the shell profile. A comprehensive guide how
to do it correctly can be found in the manual page (`perldoc local::lib`,
or online at [local::lib](https://metacpan.org/pod/local::lib)).

Essentially, it boils down to adding the following line to your shell profile
(e.g. `.bash_profile`, `.bashrc` for bash):

    eval "$(perl -I$HOME/perl5/lib/perl5 -Mlocal::lib)"

The inner perl command will print roughly the following output, which then gets
evaluated by the shell to update the environment accordingly.

    PATH="/home/<user>/perl5/bin${PATH:+:${PATH}}"; export PATH;
    PERL5LIB="/home/<user>/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
    PERL_LOCAL_LIB_ROOT="/home/<user>/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
    PERL_MB_OPT="--install_base \"/home/<user>/perl5\""; export PERL_MB_OPT;
    PERL_MM_OPT="INSTALL_BASE=/home/<user>/perl5"; export PERL_MM_OPT;

Testing
-------

Testing is done like this:

    $ make test
