#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

package OpenSSL::Query::ClaDB;
use Carp;
use Moo;
use OpenSSL::Query qw(-register-cla OpenSSL::Query::ClaDB -priority 0);

with q(OpenSSL::Query::Role::Bureau);

has clafile => ( is => 'ro', default => 'cladb.txt' );
has _cladb => ( is => 'lazy', builder => 1 );

sub _build__cladb {
  my $self = shift;

  my $path = $self->_find_file($self->clafile, 'CLADB');
  my $cladb = {};

  open my $clafh, $path
    or croak "Trying to open $path: $!";
  while (my $line = <$clafh>) {
    $line =~ s|\R$||;			# Better chomp
    next if $line =~ m|^#|;
    next if $line =~ m|^\s*$|;
    croak "Malformed CLADB line: $line"
      unless $line =~ m|^(\S+\@\S+)\s+([ICR])\s+(.+)$|;

    my $email = lc $1;
    my $status = $2;
    my $name = $3;
    croak "Duplicate email address: $email"
      if exists $cladb->{$email};

    $cladb->{$email} = { status => $status, name => $name };
  }
  close $clafh;

  return $cladb;
}

sub has_cla {
  my $self = shift;
  my $id = lc shift;
  if ($id =~ m|<(\S+\@\S+)>|) { $id = $1; }
  croak "Malformed input ID" unless $id =~ m|^\S+(\@\S+)$|;
  my $starid = '*' . $1;

  return exists $self->_cladb->{$id} || exists $self->_cladb->{$starid};
}

1;
