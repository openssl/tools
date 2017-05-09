#!/usr/bin/env perl

# This means that 'dance' at the end of query.psgi will not start a built in
# service, but will simply return a coderef.  This is useful to run this with
# diverse dispatchers as well as tests.
BEGIN { $ENV{DANCER_APPHANDLER} = 'PSGI';}

use Dancer2;
use FindBin '$Bin';
use lib path($Bin, '..', '..', 'lib'), path($Bin, '..', 'lib');
use Plack::Handler::CGI;
use Plack::Util;

# For some reason Apache SetEnv directives dont propagate
# correctly to the dispatchers, so forcing PSGI and env here
# is safer.
set apphandler => 'PSGI';
set environment => 'production';

my $app = Plack::Util::load_psgi( path($Bin, '..', 'bin', 'query.psgi') );
die "Unable to read startup script: $@" if $@;
Plack::Handler::CGI->new()->run($app);
