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

OpenSSL::Query requires these extra modules to run:

- YAML::XS			(debian package libyaml-libyaml-perl)
- Moo				(debian package libmoo-perl)
- Dancer2			(debian package libdancer2-perl)
- Plack				(debian package libplack-perl)
- OpenSSL::Query		(from ../OpenSSL-Query)

Any other module OpenSSL::Query depends on should be part of core
perl.

Installation
------------

    $ perl Makefile.PL
    $ make
    $ make install

Testing
-------

Testing is done like this:

    $ make test
