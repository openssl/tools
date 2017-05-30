#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

package OpenSSL::Query::PersonREST;
use Carp;
use Moo;
use OpenSSL::Query qw(-register-person OpenSSL::Query::PersonREST -priority 1);
use LWP::UserAgent;
use URI::Encode qw(uri_encode uri_decode);
use JSON::PP;
use Data::Dumper;

has base_url => ( is => 'ro', default => 'https://api.openssl.org' );
has _personhandler => ( is => 'lazy', builder => 1 );

sub _build__personhandler {
  return LWP::UserAgent->new();
}

# Validation
sub BUILD {
  my $self = shift;

  # print STDERR Dumper(@_);
  my $ua = $self->_personhandler;
  my $resp = $ua->get($self->base_url);
  croak "Server error: ", $resp->message if $resp->is_server_error;
}

sub find_person {
  my $self = shift;
  my $id = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url . '/0/Person/'
			  . uri_encode($id, {encode_reserved => 1}));
  return () unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return wantarray ? %$decoded : scalar keys %$decoded > 0;
}

sub find_person_tag {
  my $self = shift;
  my $id = shift;
  my $tag = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url
		      . '/0/Person/'
		      . uri_encode($id, {encode_reserved => 1})
		      . '/ValueOfTag/'
		      . uri_encode ($tag, {encode_reserved => 1}));
  return undef unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return $decoded->[0];
}

sub is_member_of {
  my $self = shift;
  my $id = shift;
  my $group = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url
		      . '/0/Person/'
		      . uri_encode($id, {encode_reserved => 1})
		      . '/IsMemberOf/'
		      . uri_encode ($group, {encode_reserved => 1}));
  return 0 unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return $decoded->[0];
}

# Group methods
sub members_of {
  my $self = shift;
  my $group = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url
		      . '/0/Group/'
		      . uri_encode($group, {encode_reserved => 1})
		      . '/Members');
  return () unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return @$decoded;
}

1;
