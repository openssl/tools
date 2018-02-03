#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;
use warnings;

# OpenSSL git version utilities.

# Retrieve list of branches and release tags in a reference usable by other
# functions.

sub openssl_git_init {
    my @tmpbranches =
      grep { chomp; s|^\s+origin/OpenSSL_(\w*\d)-stable$|$1|; } `git branch -r`;
    die "Error retrieving branch details!" if $?;

    # Create initial dev version entry: lowest possible version for
    # branch which will be accurate if no releases have take place.
    my @branches;
    foreach ( sort @tmpbranches ) {
        tr/_/\./;
        next if /^0/ && $_ ne "0.9.8";
        push @branches, $_;
    }

    # Create list of tags
    my @rtags = grep { chomp; s/OpenSSL_(\d.*)$/$1/; } `git tag`;
    die "Error retrieving tag details!" if $?;
    my @tags;
    foreach (@rtags) {

        # Skip if tag has - and it isn't pre
        next if ( /-/ && !/-pre\d+$/ );
        tr/_/\./;
        next if /^0/ && !/^0.9.8/;
        push @tags, $_;
    }
    my $aref = [ \@tags, \@branches ];
    return $aref;
}

# Return last release number on supplied branch.
# If $nopre is set, skip pre releases, if $prev set
# return last release on previous branch if no release
# on current branch.

sub openssl_git_last_release {
    my ( $rinfo, $branch, $nopre, $prev ) = @_;
    my ( $rtag, $rbranch ) = @$rinfo;
    my $brhex = openssl_version_branch_hex($branch);
    my $rv    = "";
    my $rvhex = "";
    foreach (@$rtag) {
        next if ( $nopre && /-pre/ );
        my $taghex  = openssl_version_hex($_);
        my $tagbhex = openssl_version_branch_hex($_);

        # Is tag for current branch?
        if ( $tagbhex ne $brhex ) {

            # Discard if only want current branch or greater
            # than current branch
            next if ( !$prev || $tagbhex gt $brhex );
        }

        # If release is later than last value replace.
        if ( $taghex gt $rvhex ) {
            $rv    = $_;
            $rvhex = openssl_version_hex($rv);
        }
    }
    return $rv eq "" ? "none" : $rv;
}

sub openssl_git_current_branch {

    # Current branch
    $_ = `git rev-parse --abbrev-ref HEAD`;
    die "Can't get current branch!" if $?;
    chomp;
    return $_;
}

sub openssl_git_branch_version {
    ($_) = @_;
    $_ = openssl_git_current_branch() unless defined $_;
    die "Unexpected  branch name $_" unless s/OpenSSL_//;
    tr /_/\./;
    die "Unexpected  branch name $_" unless s/-stable$//;
    return $_;
}

sub openssl_git_expected_version {
    my ( $rinfo, $branch ) = @_;
    $branch = openssl_git_major_version() unless defined $branch;
    my $rv = openssl_git_last_release( $rinfo, $branch );
    return $branch .= "-dev" if $rv eq "none";
    return openssl_version_next($rv);
}

sub openssl_git_check_changes {

    # For some reason this is unreliable if you use --quiet ...
    system("git diff --exit-code >/dev/null");
    return 0 if $? == 0;
    return 1 if $? == 256;
    die "Unexpected status $?";
}

sub openssl_git_make_update {
    print "Configuring system\n";
    system("perl Configure gcc >/dev/null 2>&1");
    die "Error configuring system" if $?;

    print "Doing make update\n";
    system("make update >/dev/null 2>&1");
    die "make update error" if $?;
    if ( openssl_git_check_changes() ) {
        print "Source modified, committing changes\n";
        openssl_git_commit( "make update", @_ );
        die "Error committing update" if $?;
    } else {
        print "No changes\n";
    }
    system("find . -name Makefile.save -exec rm \\\{\\\} \\\;");
    die "Error removing Makefile.save files" if $?;
}

sub openssl_git_delete_local_tags {
    my ($branch) = @_;
    $branch =~ s/-stable//;
    my @tags = grep { chomp; } `git tag -l $branch\*`;
    my @rtags =
      grep { chomp; s|^.*refs/tags/||; } `git ls-remote --tags origin`;
    my %rtaghash;
    foreach (@rtags) {
        $rtaghash{$_} = 1;
    }
    foreach (@tags) {
        if ( !defined $rtaghash{$_} ) {
            print "Deleting local tag $_\n" if $main::verbose;
            system("git tag -d $_");
        }
    }
}

sub openssl_git_commit {
    my @args = ( "git", "commit", "-a" );
    my ( $message, @reviewers ) = @_;
    $message .= "\n\n";
    foreach (@reviewers) {
        $message .= "Reviewed-by: $_\n";
    }
    push @args, "-m", "$message";
    system(@args);
    die "Error committing update" if $?;
}

return 1;
