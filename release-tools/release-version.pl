#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

use strict;
use warnings;

# OpenSSL version utility functions.

# Convert string version to hex format
# usage is version_hex($version_string, $tag)
# where "tag" is 1 if the version comes from a git tag.
# Return version in hex format.

sub openssl_version_hex {
    my ( $version, $tag ) = @_;
    my $ov = $version;
    $tag = $version =~ /_/ unless defined $tag;
    $version =~ tr/_/\./ if $tag;

    # Separate version string into fields and convert each one.

    if ( !( $version =~ /([\d])\.([\d]+).([\d]+)(.*)$/ ) ) {
        die "Invalid version syntax \"$version\"";
    }
    my $M    = $1;
    my $NN   = sprintf "%02x", $2;
    my $FF   = sprintf "%02x", $3;
    my $rest = $4;

    if ( length $M > 1 || length $NN > 2 || length $FF > 2 ) {
        die "Invalid version syntax";
    }

    my ( $PP, $S );

    if ( $rest eq "" ) {
        $PP = "00";
        $S  = "f";
    } else {
        $S = "";
        if ( $rest =~ s/-dev$// ) {
            $S = "0";
        }

        # Note pre release development versions of the form -preX-dev
        # version is same for pre release and development versions
        # So check for -preX after we have stripped off any
        # -dev above.
        if ( $rest =~ s/-pre([\d]+)$// ) {
            $S = sprintf "%x", $1;
        }

        # No -dev or -pre, must be release
        $S = "f" if $S eq "";

        if ( $rest eq "" ) {
            $PP = "00";
        } elsif ( $rest =~ /^z([a-z]$)/ ) {
            $PP = sprintf "%02x", ord($1) - ord("a") + 26;
        } elsif ( $rest =~ /(^[a-z]$)/ ) {
            $PP = sprintf "%02x", ord($1) - ord("a") + 1;
        } else {
            die "Invalid version syntax: \"$ov\"";
        }
    }

    if ( length $S > 1 || length $PP > 2 ) {
        die "Invalid version syntax";
    }

    return "0x$M$NN$FF$PP$S";

}

# Convert hex format to string
# Usage is version_str($hex_version), returns version as a string.

sub openssl_version_str {
    my ($hexversion) = @_;
    my ( $chk, $M, $NN, $FF, $PP, $S ) = unpack "A2AA2A2A2A", $hexversion;
    die "Bad hex version $hexversion" if $chk ne "0x" || $S eq "";
    my $version_str = hex($M) . "." . hex($NN) . "." . hex($FF);

    if ( $PP ne "00" ) {
        my $hex_PP = hex($PP);
        if ( $hex_PP > 25 ) {
            $version_str .= "z";
            $hex_PP -= 25;
        }
        $version_str .= chr( $hex_PP + ord("a") - 1 );
    }

    if ( $S eq "0" ) {
        $version_str .= "-dev";
    } elsif ( $S ne "f" ) {
        $version_str .= "-pre" . hex($S);
    }

    return $version_str;

}

# Given a hex number work out the next version.
# Usage is openssl_next_version($version, $pre, $dev)
# $pre indicates whether we should use pre releases
# $dev indicates we should use a development version.

sub openssl_version_next {
    my ( $version, $pre, $dev ) = @_;
    my $hexversion = openssl_version_hex($version);
    my ( $chk, $M, $NN, $FF, $PP, $S ) = unpack "A2AA2A2A2A", $hexversion;
    die "Invalid syntax $version" if $S eq "";

    # If $pre or $dev not set work out what we want.
    $dev = $version !~ /-dev/ unless defined $dev;
    $pre = $version =~ /-pre/ unless defined $pre;

    # If we want a release then just need to get rid of "-dev" part.
    #
    if ( $dev == 0 ) {
        die "Expecting a development version!!" if $version !~ /-dev/;

        # NB version number is identical for pre and pre development.
        # So just strip out "-dev" part.
        $version =~ s/-dev//;

        # Special case: if we are going from X.Y.Z-dev and using pre releases
        # next version is X.Y.Z-pre1-dev and this wont be a release,
        # just changing version numbers for beginning of pre releases.
        $version .= "-pre1-dev" if $pre && $S eq "0";

        # If moving out of pre release return full release
        $version =~ s/-pre.*$// unless $pre;
        return $version;
    }
    die "Not expecting a development version!!" if $version =~ /-dev/;

    # If a pre release we need to increment the pre release portion
    if ( $pre != 0 ) {

        # Hex version can only handle 14 pre releases.
        die "Can't go past pre release 14!!" if ( $S eq "e" );

        # Must be a pre release or development version.
        die "Can't go from release to pre release!!" if $S eq "f";
        $S = sprintf "%x", hex($S) + 1;
        $hexversion =~ s/.$/$S/;
        $version = openssl_version_str($hexversion);
        $version .= "-dev" if $dev;
        return $version;
    }

   # If last version pre release and not doing pre releases any more then switch
   # to full release.
    return openssl_version_str("0x$M$NN$FF${PP}f") if ( $version =~ /pre/ );

    # Otherwise need to increment letter value if not a pre release.
    $PP = sprintf "%02x", hex($PP) + 1;
    die "Invalid letter version!!" if ( length $PP > 2 );
    return openssl_version_str("0x$M$NN$FF${PP}0");
}

# Return hex branch version belongs to.
# So "1.0.1a-pre2-dev" returns hex of "1.0.1" for example.

sub openssl_version_branch_hex {
    my ($version) = @_;
    my $hexversion = openssl_version_hex($version);
    my ( $chk, $M, $NN, $FF, $PP, $S ) = unpack "A2AA2A2A2A", $hexversion;
    die "Invalid syntax $version" if $S eq "";
    return "0x$M$NN${FF}00F";
}

return 1;
