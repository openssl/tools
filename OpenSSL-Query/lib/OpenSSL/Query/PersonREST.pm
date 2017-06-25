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
use HTTP::Status qw(:is);
use URI::Encode qw(uri_encode uri_decode);
use JSON::PP;
use Data::Dumper;

has base_url => ( is => 'ro', default => 'https://api.openssl.org' );
has _personhandler => ( is => 'lazy', builder => 1 );

sub _build__personhandler {
  my $ua = LWP::UserAgent->new( keep_alive => 1 );
  $ua->env_proxy;
  return $ua;
}

sub list_people {
  my $self = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url . '/0/People');
  croak "Server error: ", $json->message if is_server_error($json->code);
  return () unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return @$decoded;
}

sub _id_encode {
  my $id = shift;

  return $id if ref($id) eq "";
  croak "Malformed input ID" if ref($id) ne "HASH" || scalar keys %$id != 1;

  my $tag = (keys %$id)[0];
  return $tag . ':' . $id->{$tag};
}

sub find_person {
  my $self = shift;
  my $id = _id_encode(shift);

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url . '/0/Person/'
			  . uri_encode($id, {encode_reserved => 1}));
  croak "Server error: ", $json->message if is_server_error($json->code);
  return () unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return wantarray ? %$decoded : scalar keys %$decoded > 0;
}

sub find_person_tag {
  my $self = shift;
  my $id = _id_encode(shift);
  my $tag = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url
		      . '/0/Person/'
		      . uri_encode($id, {encode_reserved => 1})
		      . '/ValueOfTag/'
		      . uri_encode ($tag, {encode_reserved => 1}));
  croak "Server error: ", $json->message if is_server_error($json->code);
  return undef unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return $decoded->[0];
}

sub is_member_of {
  my $self = shift;
  my $id = _id_encode(shift);
  my $group = shift;

  my $ua = $self->_personhandler;
  my $json = $ua->get($self->base_url
		      . '/0/Person/'
		      . uri_encode($id, {encode_reserved => 1})
		      . '/IsMemberOf/'
		      . uri_encode ($group, {encode_reserved => 1}));
  croak "Server error: ", $json->message if is_server_error($json->code);
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
  croak "Server error: ", $json->message if is_server_error($json->code);
  return () unless $json->code == 200;

  my $decoded = decode_json $json->decoded_content;

  return @$decoded;
}

1;
