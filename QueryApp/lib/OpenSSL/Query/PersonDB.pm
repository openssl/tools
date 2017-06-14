#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

package OpenSSL::Query::PersonDB;

use Carp;
use Clone qw(clone);
use Moo;
use OpenSSL::Query qw(-register-person OpenSSL::Query::PersonDB -priority 0);

with q(OpenSSL::Query::Role::Bureau);

has personfile => ( is => 'ro', default => 'persondb.yaml' );
has _persondb => ( is => 'lazy', builder => 1 );

use YAML::XS qw(LoadFile);

sub _build__persondb {
  my $self = shift;

  my $yaml =
    LoadFile( $self->_find_file($self->personfile, 'PERSONDB') );

  croak "Malformed PersonDB" unless ref($yaml) eq "ARRAY";
  foreach (@{$yaml}) {
    croak "Malformed PersonDB"
      unless (defined($_->{ids}) and defined($_->{memberof})
	      and ref($_->{ids}) eq "ARRAY" and ref($_->{memberof}) eq "HASH");
  }

  return $yaml;
}

sub list_people {
  my $self = shift;

  my @list = ();
  foreach my $record (@{$self->_persondb}) {
    push @list, clone($record->{ids});
  }

  return @list;
}

sub find_person {
  my $self = shift;
  my $id = shift;

  if (ref($id) eq "" && $id =~ m|<(\S+\@\S+)>|) { $id = $1; }
  croak "Malformed input ID" if ref($id) eq "HASH" and scalar keys %$id != 1;

  my $found = 0;
  foreach my $record (@{$self->_persondb}) {
    foreach my $rid (@{$record->{ids}}) {
      if (ref($id) eq "") {
	if (ref($rid) eq "HASH") {
	  foreach (keys %$rid) {
	    last if $found = $id eq $rid->{$_};
	  }
	} else {
	  $found = $id eq $rid;
	}
      } elsif (ref($id) eq "HASH" && ref($rid) eq "HASH") {
	foreach (keys %$rid) {
	  last if $found = exists $id->{$_} && $id->{$_} eq $rid->{$_};
	}
      }

      return (wantarray ? %$record : 1) if $found;
    }
  }
  return wantarray ? () : 0;
}

sub find_person_tag {
  my $self = shift;
  my $id = shift;
  my $tag = shift;

  my %record = $self->find_person($id);
  return $record{tags}->{$tag};
}

sub is_member_of {
  my $self = shift;
  my $id = shift;
  my $group = shift;

  if ($id =~ m|<(\S+\@\S+)>|) { $id = $1; }

  my %record = $self->find_person($id);
  return $record{memberof}->{$group}
    if exists $record{memberof}->{$group};
  return 0;
}

sub members_of {
  my $self = shift;
  my $group = shift;

  my @ids = ();
  foreach my $record (@{$self->_persondb}) {
    if (grep { $_ eq $group } keys %{$record->{memberof}}) {
      push @ids, [ @{$record->{ids}} ];
    }
  }
  return @ids;
}

1;
