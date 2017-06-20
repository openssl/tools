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

- Module::Starter and its dependencies (debian package libmodule-starter-perl)
- Module::Install		(debian package libmodule-install-perl)

OpenSSL::Query requires these extra modules to run:

- YAML::XS			(debian package libyaml-libyaml-perl)
- Moo				(debian package libmoo-perl)
- Dancer2			(debian package libdancer2-perl)
- Plack				(debian package libplack-perl)
- URI::Encode			(debian package liburi-encode-perl)
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

To get the paths right permanently, you might want to consider adding
this in your `.bash_profile`, `.bashrc` och corresponding shell init
script:

    eval "`perl -I$HOME/perl5/lib/perl5 -Mlocal::lib`"

Testing
-------

Testing is done like this:

    $ make test
