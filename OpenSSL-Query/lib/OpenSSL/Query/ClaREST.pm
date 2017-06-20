#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

package OpenSSL::Query::ClaREST;
use Carp;
use Moo;
use OpenSSL::Query qw(-register-cla OpenSSL::Query::ClaREST -priority 1);
use HTTP::Status qw(:is);
use LWP::UserAgent;
use URI::Encode qw(uri_encode uri_decode);
use JSON::PP;
use Data::Dumper;

has base_url => ( is => 'ro', default => 'https://api.openssl.org' );
has _clahandler => ( is => 'ro', builder => 1 );

sub _build__clahandler {
  return LWP::UserAgent->new( keep_alive => 1 );
}

sub has_cla {
  my $self = shift;
  my $id = shift;
  if ($id =~ m|<(\S+\@\S+)>|) { $id = $1; }
  croak "Malformed input ID" unless $id =~ m|^\S+(\@\S+)$|;

  my $ua = $self->_clahandler;
  my $json = $ua->get($self->base_url . '/0/HasCLA/'
		      . uri_encode($id, {encode_reserved => 1}));
  croak "Server error: ", $json->message if is_server_error($json->code);
  return $json->code == 200;
}

1;
