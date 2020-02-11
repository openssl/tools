OpenSSL::Query
==============

A module to query certain information about OpenSSL committers as well
as members of the OMC (OpenSSL Management Committee).  These data are
usually interesting for other programs that need to verify identities,
whether a certain person holds a CLA, that sort of thing.

OpenSSL::Query is built to be able to handle several implementations
for access to the databases that hold the data.  The default
implementation uses a RESTful API with JSON encoded responses,
OpenSSL::Query::REST.

Requirements
------------

OpenSSL::Query requires the following modules to build:

- Module::Install		(debian package libmodule-install-perl)

OpenSSL::Query requires these extra modules to run:

- Class::Method::Modifiers	(debian package libclass-method-modifiers-perl)
- Moo				(debian package libmoo-perl)
- URI::Encode			(debian package liburi-encode-perl)
- LWP::UserAgent
- LWP::Protocol::https

Any other module OpenSSL::Query depends on should be part of core
perl.

Installation
------------

    perl Makefile.PL
    make && make install

Local installation
------------

For a local installation, you might want to consider using local::lib
(debian package liblocal-lib-perl).  In that case, running Makefile.PL
is slightly different:

    perl -Mlocal::lib Makefile.PL

Other than that, follow the instructions in "Installation" above.

To get the paths right permanently, you might want to consider adding
this in your `.bash_profile`, `.bashrc` och corresponding shell init
script:

    eval "`perl -I$HOME/perl5/lib/perl5 -Mlocal::lib`"

Testing
-------

Testing is done like this:

    make test

However, it requires that a temporary query service is started as
well.  This is part of QueryApp, and is started like this:

    here=`pwd`                # the directory OpenSSL-Query/
    cd ../QueryApp            # Or wherever you have it checked out
    PERSONDB=./t/query_data/pdb.yaml CLADB=./t/query_data/cdb.txt \
    PERL5LIB=./lib:$here/lib plackup bin/query.psgi
