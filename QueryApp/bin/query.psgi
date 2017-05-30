#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;
use warnings;
use Carp;

# Currently supported API versions:</p>
#
# /0 : Version 0
#
# Version 0 API:
#
# /0/Person/:name
#
#     Fetches the complete set of database information on :name.
#
# /0/Person/:name/Membership
#
#     Fetches the groups (omc, omc-alumni or commit) that :name is
#     member of, with the date they became or were reinstated in the group
#
# /0/Person/:name/IsMemberOf/:group
#
#     Fetches from what date :name became or was reinstated as member
#     of :group
#
# /0/Person/:name/ValueOfTag/:tag
#
#     Fetches the value of :tag associated with :name.  This tag is
#     usually application specific.
#
# /0/Person/:name/HasCLA
#
#     Fetches the identity under which :name has a CLA, if any.
#
# /0/HasCLA/:id
#
#     Checks if there is a CLA under the precise identity :id.  This
#     differs from /0/Person/:name/HasCLA in that it demands the precise
#     identity (email address or committer id) that the CLA is registered
#     under, while /0/Person/:name/HasCLA checks for any CLA associated
#     with any of :name's identities and returns a list of what it finds.

package query;
use Dancer2;
use HTTP::Status qw(:constants);
use OpenSSL::Query::DB;
use URI::Encode qw(uri_decode);

set serializer => 'JSON';
set bureau => '/var/cache/openssl/checkouts/bureau';

# Version 0 API.
# Feel free to add new routes, but never to change them or remove them,
# or to change their response.  For such changes, add a new version at
# the end

prefix '/0';

get '/Person/:name' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau});
  my $name = uri_decode(route_parameters->get('name'));
  my %response = $query->find_person($name);

  return { %response } if %response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/Person/:name/Membership' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $name = uri_decode(route_parameters->get('name'));
  my %response = $query->find_person($name);

  return $response{memberof} if %response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/Person/:name/IsMemberOf/:group' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $name = uri_decode(route_parameters->get('name'));
  my $group = uri_decode(route_parameters->get('group'));
  my $response = $query->is_member_of($name, $group);

  return [ $response ] if $response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/Person/:name/ValueOfTag/:tag' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $name = uri_decode(route_parameters->get('name'));
  my $tag = uri_decode(route_parameters->get('tag'));
  my $response = $query->find_person_tag($name, $tag);

  return [ $response ] if $response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/Person/:name/HasCLA' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $name = uri_decode(route_parameters->get('name'));
  my %person = $query->find_person($name);
  my @response = ();

  foreach (@{$person{ids}}) {
    next if (ref $_ eq "HASH");
    push @response, $_ if $query->has_cla($_);
  }
  return [ @response ] if @response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/Group/:group/Members' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $group = uri_decode(route_parameters->get('group'));
  my @response = $query->members_of($group);

  return [ @response ] if @response;
  send_error('Not found', HTTP_NO_CONTENT);
};

get '/HasCLA/:id' => sub {
  my $query = OpenSSL::Query->new(bureau => config->{bureau}, REST => 0);
  my $id = uri_decode(route_parameters->get('id'));
  my $response = $query->has_cla($id);

  return [ $response ] if $response;
  send_error('Not found', HTTP_NO_CONTENT);
};

# End of version 0 API.  To create a new version, start with `prefix '1';'
# below.

dance;
