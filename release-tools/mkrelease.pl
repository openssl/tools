#! /usr/bin/env perl
# Copyright 2010-2018 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the OpenSSL license (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# OpenSSL release generation script.

use strict;
use warnings;
use File::Basename;
use lib dirname(__FILE__);
use Module::Load::Conditional qw(can_load);
can_load(modules => { 'OpenSSL::Query::DB' => undef });
use OpenSSL::Query::REST;

require "release-check.pl";
require "release-date.pl";
require "release-git.pl";
require "release-update.pl";
require "release-version.pl";

our $debug   = 0;
our $verbose = 0;
my @reviewers;
my @openssl_branches;
my $revert;
my $pre;
my $info_only;
my $branch_info_only;
my $no_clean;
my $no_update;
my $no_release;
my $no_upload;
my $bversion;
my $ok;
my $label;

#Determine include path
our $includepath;
if ( -e "crypto/opensslv.h" ) {
    $includepath = "crypto";
}
else {
    $includepath = "include/openssl";
}

sub print_git_info {
    my ( $rinfo, $branch, $s ) = @_;
    my $version = openssl_git_expected_version( $rinfo, $branch );
    my $last = openssl_git_last_release( $rinfo, $branch );
    my $last_full = openssl_git_last_release( $rinfo, $branch, 1, 1 );

    # Auto detect pre release if we haven't forced it.
    $pre = $version =~ /-pre/ unless defined $pre;
    my $next = openssl_version_next( $version, $pre );

    print "${s}Branch version:    $branch\n";
    print "${s}Last release:      $last\n";
    print "${s}Last full release: $last_full\n";
    print "${s}Current version:   $version\n";
    print "${s}Next release:      $next\n";
}

sub print_branch_info {
    my ($rinfo) = @_;
    my ( $rtags, $rbranches ) = @$rinfo;
    print "All Branch details:\n";
    foreach (@$rbranches) {
        print "\n";
        print_git_info( $rinfo, $_, "\t" );
    }
    print "\n";
}

# Initialise git version tables, OMC database.
my $gitinfo = openssl_git_init();
my $query = OpenSSL::Query->new();

foreach (@ARGV) {
    if (/^--git-info$/) {
        $info_only = 1;
    } elsif (/^--branch-version=(.*)$/) {
        $bversion = $1;
    } elsif (/^--git-branch-info/) {
        $branch_info_only = 1;
    } elsif (/^--no-clean/) {
        $no_clean = 1;
    } elsif (/^--no-release/) {
        $no_release = 1;
    } elsif (/^--no-update/) {
        $no_update = 1;
    } elsif (/^--no-upload/) {
        $no_upload = 1;
    } elsif (/^--revert/) {
        $revert = 1;
    } elsif (/^--leave-pre/) {
        $pre = 0;
    } elsif (/^--enter-pre/) {
        $pre = 1;
    } elsif (/^--debug/) {
        $debug   = 1;
        $verbose = 1;
    } elsif (/^--verbose/) {
        $verbose = 1;
    } elsif (/^--reviewer=(.*)$/) {
	my $r = $1;
	my $rname = $query->find_person_tag($r, 'rev');
        die "Unknown reviewer $1" unless $rname;
        push @reviewers, $rname;
    } elsif (/^--label=(.*)$/) {
        $label = $1;
        if ( $label ne "alpha" && $label ne "beta" ) {
            die "Invalid label";
        }
    } else {
        print "Uknown option $_\n";
        exit 1;
    }
}

if ($revert) {
    $_ = openssl_git_current_branch();
    print "Reverting to repository version for $_\n";
    system("git reset --hard origin/$_");
    die "Error reverting!!" if $?;
    openssl_git_delete_local_tags($_);
    exit 0;
}

$bversion = openssl_git_branch_version() unless defined $bversion;

if ($info_only) {
    print_git_info( $gitinfo, $bversion, "" );
    exit 0;
}

if ($branch_info_only) {
    print_branch_info($gitinfo);
    exit 0;
}

die "No reviewer set!" unless @reviewers;

print "Current branch version is $bversion\n";

if ( openssl_git_check_changes() ) {
    print "ERROR: unstaged changes in current branch!\n";
    exit 1;
}

my $expected_version = openssl_git_expected_version( $gitinfo, $bversion );

# If this is first pre release there will be no releases from this branch
# So set expected version to pre1-dev as we can't detect this from
# tags.

if ( $expected_version !~ /-pre/ && openssl_check_first_pre() ) {
    $expected_version =~ s/-dev/-pre1-dev/;
}

# Auto detect pre release if we haven't forced it.
$pre = $expected_version =~ /-pre/ unless defined $pre;

if ( !$pre && defined $label ) {
    die "Not a pre-release but a label has been defined";
}
if ( $pre && !defined $label ) {
    die "This is a pre-release but a label has not been defined";
}

my $last_version = openssl_git_last_release( $gitinfo, $bversion, 1, 1 );
my $last_branch_release = openssl_git_last_release( $gitinfo, $bversion, 1 );
my $next_version = openssl_version_next( $expected_version, $pre );

print "Branch feature version:      $bversion\n";
print "Last release on this branch: $last_branch_release\n";
print "Current branch version       $expected_version\n";
print "Next release version         $next_version\n";
print "Last full release version    $last_version\n";

$ok = openssl_check_all( $expected_version, $last_version );

print "Branch sanity check: " . ( $ok ? "OK" : "NOT OK" ) . "\n";

if ( $ok == 0 ) {
    print "Sanity check failed, cannot continue\n";
    exit 1;
}

if ( !$no_clean ) {
    print "Cleaning directory\n";
    system("git clean -x -d -f");
    die "Error cleaning directory" if $?;
}

openssl_git_make_update(@reviewers) unless $no_update;

$expected_version = openssl_version_next( $expected_version, $pre );

my $date = openssl_current_date() unless $expected_version =~ /-pre1-dev/;

print "Updating versions to $expected_version\n";

openssl_update_all( $expected_version, $date, $label );

$ok = openssl_check_all( $expected_version, $last_version, $date );

print "Changes sanity check: " . ( $ok ? "OK" : "NOT OK" ) . "\n";

if ( $ok == 0 ) {
    print "Release sanity check failed, cannot continue\n";
    exit 1;
}

print "Committing changes:\n";

# If we changed from -dev to -pre1-dev a dev version is
# entering pre release. Just commit changes without a release.

if ( $expected_version =~ /pre1-dev/ ) {
    my $main_version = $expected_version;
    $main_version =~ s/-pre1-dev//;
    openssl_git_commit( "OpenSSL $main_version is now in pre release",
        @reviewers );
    die "Error comitting changes!" if $?;
    print "Version set to $expected_version, exiting\n";
    exit 0;
}

openssl_git_commit( "Prepare for $expected_version release", @reviewers );
die "Error comitting release changes!" if $?;

my $tag = "OpenSSL_$expected_version";
my $tagkey =
  defined( $ENV{OPENSSL_GPG_KEYID} ) ? " -u $ENV{OPENSSL_GPG_KEYID}" : " -s";

$tag =~ tr/\./_/;

print
  "Tagging release with tag $tag (you will need to provide a pass phrase)\n";

system("git tag$tagkey -m \"OpenSSL $expected_version release tag\" $tag");
die "Error tagging release!" if $?;

my $TAR = defined( $ENV{OPENSSL_TAR} ) ? "TAR=$ENV{OPENSSL_TAR}" : "";

if ( !$no_release ) {
    print "Generating release tarball.\n";
    my $openssl = $ENV{"OPENSSL"} // "openssl";
    my $gpgkeyid =
      defined( $ENV{OPENSSL_GPG_KEYID} ) ? " -u $ENV{OPENSSL_GPG_KEYID}" : "";
    my $gpg    = $ENV{"OPENSSL_GPG"}     // "gpg$gpgkeyid";
    my $gpgtar = $ENV{"OPENSSL_GPG_TAR"} // "$gpg --use-agent -sba";
    my $gpgann = $ENV{"OPENSSL_GPG_ANNOUNCE"}
      // "$gpg --use-agent -sta --clearsign";
    my $tarfile = "openssl-${expected_version}.tar.gz";
    system("(./config; make $TAR dist) >../$tarfile.log 2>&1");
    die "Error generating release!" if $?;
    die "Can't find tarball!!" unless -f "../$tarfile";

    my $length = -s "../$tarfile";
    print "Creating hash files\n";
    my $sha1hash = `$openssl sha1 < ../$tarfile`;
    chomp $sha1hash;
    $sha1hash =~ s/^.*=\s//;
    die "invalid hash" unless $sha1hash =~ /[0-9a-f]{20}/;
    my $sha256hash = `$openssl sha256 < ../$tarfile`;
    chomp $sha256hash;
    $sha256hash =~ s/^.*=\s//;
    die "invalid hash" unless $sha256hash =~ /[0-9a-f]{20}/;
    open OUT, ">../$tarfile.sha1";
    print OUT $sha1hash . "\n";
    close OUT;
    open OUT, ">../$tarfile.sha256";
    print OUT $sha256hash . "\n";
    close OUT;
    print "Creating PGP signature:\n";
    unlink("../${tarfile}.asc");
    system("$gpgtar ../$tarfile");
    die "Error creating signature" if $?;

    my $anntxt = "../openssl-${expected_version}.txt";

    open OUT, ">$anntxt";
    if ( $expected_version =~ /-pre/ ) {

        # Note the variable name is the same length as the real
        # version so the announcement can be made to look pretty.
        # If we ever go to pre10 it will be one character longer...
        my $openssl_ver = $expected_version;
        $openssl_ver =~ s/^(.*)-pre(\d+)$/$1 pre release $2/;
        my $fvers = $expected_version;
        $fvers =~ s/-pre\d+//;
        print OUT <<EOF;

   OpenSSL version $openssl_ver ($label)
   ===========================================

   OpenSSL - The Open Source toolkit for SSL/TLS
   https://www.openssl.org/

   OpenSSL $fvers is currently in $label. OpenSSL $openssl_ver has now
   been made available. For details of changes and known issues see the
   release notes at:

        https://www.openssl.org/news/openssl-$bversion-notes.html

   Note: This OpenSSL pre-release has been provided for testing ONLY.
   It should NOT be used for security critical purposes.

   The $label release is available for download via HTTP and FTP from the
   following master locations (you can find the various FTP mirrors under
   https://www.openssl.org/source/mirror.html):

     * https://www.openssl.org/source/
     * ftp://ftp.openssl.org/source/

   The distribution file name is:

    o $tarfile
      Size: $length
      SHA1 checksum: $sha1hash
      SHA256 checksum: $sha256hash

   The checksums were calculated using the following commands:

    openssl sha1 $tarfile
    openssl sha256 $tarfile

   Please download and check this $label release as soon as possible.
   To report a bug, open an issue on GitHub:

    https://github.com/openssl/openssl/issues

   Please check the release notes and mailing lists to avoid duplicate
   reports of known issues. (Of course, the source is also available
   on GitHub.)

   Yours,

   The OpenSSL Project Team.

EOF
    } else {
        # Using $avers so its length is similar to a real version
        # length so it's easier to make the announcement look pretty.
        my $avers = $expected_version;
        print OUT <<EOF;

   OpenSSL version $avers released
   ===============================

   OpenSSL - The Open Source toolkit for SSL/TLS
   https://www.openssl.org/

   The OpenSSL project team is pleased to announce the release of
   version $avers of our open source toolkit for SSL/TLS. For details
   of changes and known issues see the release notes at:

        https://www.openssl.org/news/openssl-$bversion-notes.html

   OpenSSL $avers is available for download via HTTP and FTP from the
   following master locations (you can find the various FTP mirrors under
   https://www.openssl.org/source/mirror.html):

     * https://www.openssl.org/source/
     * ftp://ftp.openssl.org/source/

   The distribution file name is:

    o $tarfile
      Size: $length
      SHA1 checksum: $sha1hash
      SHA256 checksum: $sha256hash

   The checksums were calculated using the following commands:

    openssl sha1 $tarfile
    openssl sha256 $tarfile

   Yours,

   The OpenSSL Project Team.

EOF

    }

    close OUT;
    unlink("${anntxt}.asc");
    system("$gpgann $anntxt");
    die "Cannot sign announcement file!" if $?;
    die "Signature file not found!" unless -f "$anntxt.asc";

    if ( !$no_upload ) {
        my $scp     = $ENV{OPENSSL_SCP}      // "scp";
        my $scphost = $ENV{OPENSSL_SCP_HOST} // "dev.openssl.org";
        my $scpdir  = $ENV{OPENSSL_SCP_DIR}  // "$scphost:~openssl/dist/new";
        print "Uploading release files\n";
        system(
"$scp ../$tarfile ../$tarfile.sha1 ../$tarfile.sha256 ../$tarfile.asc $anntxt.asc ${scpdir}"
        );
        die "Error uploading release files" if $?;
    }

}

$last_version = $expected_version unless $pre;
$expected_version = openssl_version_next( $expected_version, $pre );

print "Updating versions to $expected_version\n";

openssl_update_all($expected_version);

$ok = openssl_check_all( $expected_version, $last_version );

print "Sanity check: " . ( $ok ? "OK" : "NOT OK" ) . "\n";

if ( $ok == 0 ) {
    print "Sanity check failed, cannot continue\n";
    exit 1;
}

openssl_git_commit( "Prepare for $expected_version", @reviewers );
die "Error comitting release changes!" if $?;
