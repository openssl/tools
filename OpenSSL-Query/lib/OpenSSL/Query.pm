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
  my @objs = ();
  while (@packages) {
    my $obj = (shift @packages)->new(@args);
    push @objs, $obj if $obj;
  }

  croak "No implementation for $type queries" unless @objs;

  return @objs;
}

sub new {
  my $class = shift;
  my @args = @_;

  my $self = {};
  bless $self, $class;

  foreach (('person', 'cla')) {
    $self->{$_} = [ $self->_new_type($_, @args) ];
  }

  return $self;
}

sub _perform {
  my $self = shift;
  my $sub = shift;
  my $opts = shift;

  croak "\$opts MUST be a HASHref" unless ref($opts) eq "HASH";

  my @errors = ();
  foreach (@{$self->{person}}) {
    my @result = eval { $sub->($_, $opts, @_) };
    return @result unless $@;
    push @errors, $@;
  }

  croak join("\n", @errors);
}

# Person methods
sub find_person {
  my $self = shift;

  $self->_perform(sub { my $obj = shift;
			my $opts = shift;
			return $opts->{wantarray}
			  ? ($obj->find_person(@_))
			  : $obj->find_person(@_); },
		  { wantarray => wantarray }, @_);
}

sub find_person_tag {
  my $self = shift;

  $self->_perform(sub { my $obj = shift;
			my $opts = shift;
			$obj->find_person_tag(@_) },
		  { wantarray => wantarray }, @_);
}

sub is_member_of {
  my $self = shift;

  $self->_perform(sub { my $obj = shift;
			my $opts = shift;
			$obj->is_member_of(@_) },
		  { wantarray => wantarray }, @_);
}

# Group methods
sub members_of {
  my $self = shift;

  $self->_perform(sub { my $obj = shift;
			my $opts = shift;
			$obj->members_of(@_) },
		  { wantarray => wantarray }, @_);
}

# Cla methods
sub has_cla {
  my $self = shift;

  $self->_perform(sub { my $obj = shift;
			my $opts = shift;
			$obj->has_cla(@_) },
		  { wantarray => wantarray }, @_);
}

1;
