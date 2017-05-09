#! /usr/bin/env perl
#
# Copyright 2017 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;

package OpenSSL::Query;
use Carp;

our %register_impl = ();

sub import {
  my $class = shift;
  my $regtype = undef;
  my $regname = undef;
  my $regprio = 999;		# Bottom feeders

  while (scalar @_ > 0) {
    my $arg = shift;
    if ($arg eq '-register-cla') {
      $regtype = 'cla';
      $regname = shift;
    } elsif ($arg eq '-register-person') {
      $regtype = 'person';
      $regname = shift;
    } elsif ($arg eq '-priority') {
      $regprio = shift;
    } else {
      croak "Unknown argument $arg";
      return;
    }
  }
  if (!defined($regtype) || !defined($regname)) {
    croak "No proper module registration";
  }
  $register_impl{$regtype}->{$regprio}->{$regname} = 1;
}

sub _new_type {
  my $self = shift;
  my $type = shift;
  my @args = @_;

  my @packages =
    map { (sort keys %{$register_impl{$type}->{$_}}) }
    sort keys %{$register_impl{$type}};
  my $obj = undef;
  while (@packages) {
    $obj = (shift @packages)->new(@args);
    last if $obj;
  }

  croak "No implementation for $type queries" unless $obj;

  return $obj;
}

sub new {
  my $class = shift;
  my @args = @_;

  my $self = {};
  bless $self, $class;

  foreach (('person', 'cla')) {
    $self->{$_} = $self->_new_type($_, @args);
  }

  return $self;
}

# Person methods
sub find_person {
  my $self = shift;

  return wantarray
    ? ($self->{person}->find_person(@_)) : $self->{person}->find_person(@_);
}

sub find_person_tag {
  my $self = shift;

  $self->{person}->find_person_tag(@_);
}

sub is_member_of {
  my $self = shift;

  $self->{person}->is_member_of(@_);
}

# Cla methods
sub has_cla {
  my $self = shift;

  $self->{cla}->has_cla(@_);
}

1;
