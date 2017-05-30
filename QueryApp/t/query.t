#! /usr/bin/env perl

# This means that 'dance' at the end of query.psgi will not start a built in
# service, but will simply return a coderef.  This is useful to run this with
# diverse dispatchers as well as tests.
BEGIN { $ENV{DANCER_APPHANDLER} = 'PSGI';}

use strict;
use warnings;
use Test::More tests => 14;
use Plack::Test;
use Plack::Util;
use HTTP::Request::Common;
use FindBin;

# This picks up if this is part of a checkout with OpenSSLQuery
use if -r $FindBin::Bin.'/../../OpenSSLQuery/lib/OpenSSL/Query.pm',
  lib => $FindBin::Bin.'/../../OpenSSLQuery/lib';

$ENV{PERSONDB} = $FindBin::Bin.'/query_data/pdb.yaml';
$ENV{CLADB} = $FindBin::Bin.'/query_data/cdb.txt';

my $app = Plack::Util::load_psgi( $FindBin::Bin.'/../bin/query.psgi' );
my $test = Plack::Test->create( $app );

subtest 'A empty request' => sub {
  my $res = $test->request( GET '/' );
  plan tests => 1;
  ok( $res->is_error, 'Successfuly failed request' );
  note( $res->content );
};

subtest 'A empty Person request' => sub {
  my $res = $test->request( GET '/0/Person' );
  plan tests => 1;
  ok( $res->is_error, 'Successfully failed request' );
  note( $res->content );
};

subtest 'Request of person data for Ray Bradbury' => sub {
  my $res = $test->request( GET '/0/Person/Ray Bradbury' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of membership for Ray Bradbury' => sub {
  my $res = $test->request( GET '/0/Person/Ray Bradbury/Membership' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of membership in specific group for Ray Bradbury' => sub {
  my $res = $test->request( GET '/0/Person/Ray Bradbury/IsMemberOf/scifi' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of "author" tag value for Ray Bradbury' => sub {
  my $res = $test->request( GET '/0/Person/Ray Bradbury/ValueOfTag/author' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of CLA status for Ray Bradbury' => sub {
  my $res = $test->request( GET '/0/HasCLA/ray@ourplace.com' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of membership in the group "writers"' => sub {
  my $res = $test->request( GET '/0/Group/writers/Members' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  is( $res->code, 200, 'We have content' );
};

subtest 'Request of person data for Jay Luser' => sub {
  my $res = $test->request( GET '/0/Person/Jay Luser' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

subtest 'Request of membership for Jay Luser' => sub {
  my $res = $test->request( GET '/0/Person/Jay Luser/Membership' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

subtest 'Request of membership in specific group for Jay Luser' => sub {
  my $res = $test->request( GET '/0/Person/Jay Luser/IsMemberOf/scifi' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

subtest 'Request of "author" tag value for Jay Luser' => sub {
  my $res = $test->request( GET '/0/Person/Jay Luser/ValueOfTag/author' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

subtest 'Request of CLA status for Jay Luser' => sub {
  my $res = $test->request( GET '/0/HasCLA/jluser@ourplace.com' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

subtest 'Request of membership in the group "couchpotatoes"' => sub {
  my $res = $test->request( GET '/0/Group/couchpotatoes/Members' );
  plan tests => 2;
  ok( $res->is_success, 'Successful request' );
  note( $res->content );
  isnt( $res->code, 200, 'We have no content' );
};

1;
