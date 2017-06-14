#! /usr/bin/env perl

# This means that 'dance' at the end of query.psgi will not start a built in
# service, but will simply return a coderef.  This is useful to run this with
# diverse dispatchers as well as tests.
BEGIN { $ENV{DANCER_APPHANDLER} = 'PSGI';}

use strict;
use warnings;
use Test::More tests => 11;
use Data::Dumper;
use FindBin;

# This picks up if this is part of a checkout with OpenSSLQuery
use if -r $FindBin::Bin.'/../../OpenSSL-Query/lib/OpenSSL/Query.pm',
  lib => $FindBin::Bin.'/../../OpenSSL-Query/lib';
require OpenSSL::Query::DB; OpenSSL::Query::DB->import();

$ENV{PERSONDB} = $FindBin::Bin.'/query_data/pdb.yaml';
$ENV{CLADB} = $FindBin::Bin.'/query_data/cdb.txt';

my $query = OpenSSL::Query->new();

subtest 'Request of identity list' => sub {
  plan tests => 1;

  my @res = $query->list_people();
  ok( scalar @res > 0, 'We got a list' );
  note( Dumper( [ @res ] ) );
};

subtest 'Request of person data for Ray Bradbury' => sub {
  plan tests => 2;

  my $res1 = $query->find_person( 'Ray Bradbury' );
  ok( $res1, 'Ray Bradbury is present' );
  note( $res1 );

  my %res2 = $query->find_person( 'Ray Bradbury' );
  ok(scalar keys %res2 > 1, "Got Ray Bradbury's data" );
  note( Dumper( { %res2 } ) );
};

subtest 'Request of membership in specific group for Ray Bradbury' => sub {
  plan tests => 1;
  my $res = $query->is_member_of( 'Ray Bradbury', 'scifi' );
  ok( $res, "Ray Bradbury is member of scifi since ".( $res ? $res : "(unknown)" ) );
  note( $res );
};

subtest 'Request of "author" tag value for Ray Bradbury' => sub {
  plan tests => 1;
  my $res = $query->find_person_tag( 'Ray Bradbury', 'author' );
  ok( $res, "The 'author' tag for Ray Bradbury is ".( $res ? $res : "(unknown)" ) );
  note( Dumper $res );
};

subtest 'Request of CLA status for Ray Bradbury' => sub {
  plan tests => 1;
  my $res = $query->has_cla( 'ray@ourplace.com' );
  ok( $res, 'Ray Bradbury has CLA as ray@ourplace.com' );
  note( $res );
};

subtest 'Request of membership in the group "writers"' => sub {
  plan tests => 1;
  my @res = $query->members_of( 'writers' );
  ok( @res, 'Finding members of "writers"' );
  note( Dumper @res );
};

subtest 'Request of person data for Jay Luser' => sub {
  plan tests => 2;

  my $res1 = $query->find_person( 'Jay Luser' );
  ok( !$res1, 'Jay Luser is not present' );
  note( $res1 );

  my %res2 = $query->find_person( 'Jay Luser' );
  ok( !%res2, "Failed getting Jay Luser's data" );
};

subtest 'Request of membership in specific group for Jay Luser' => sub {
  plan tests => 1;
  my $res = $query->is_member_of( 'Jay Luser', 'scifi' );
  ok( !$res, 'Jay Luser is not member of scifi' );
  note( $res );
};

subtest 'Request of "author" tag value for Jay Luser' => sub {
  plan tests => 1;
  my $res = $query->find_person_tag( 'Jay Luser', 'author' );
  ok( !$res, "No 'author' tag for Jay Luser" );
  note( $res );
};

subtest 'Request of CLA status for Jay Luser' => sub {
  plan tests => 1;
  my $res = $query->has_cla( 'jluser@ourplace.com' );
  ok( !$res, 'Jay Luser has no CLA' );
  note( $res );
};

subtest 'Request of membership in the group "couchpotatoes"' => sub {
  plan tests => 1;
  my @res = $query->members_of( 'couchpotatoes' );
  ok( !@res, 'No members in "couchpotatoes"' );
  note( @res );
};

1;
