#! /bin/bash
# Copyright 2020-2023 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html

# These functions collect and manipulate information relevant for diverse
# OpenSSL versions, and populate the following variables:
#
# VERSION_FILE          The path of the file where the version information
#                       is found and should be stored.  If this is empty,
#                       no version information was found, and the release
#                       should be aborted.
# RELEASE_FILES         The set of files that must be manipulated during a
#                       release, separated by semicolons.  Other scripts are
#                       used to actually manipulate these files.
#
# MAJOR, MINOR, FIX, PATCH
#                       The three or four parts of a version number, depending
#                       on the version scheme.
#                       Examples:
#                       With OpenSSL 3.0.9, MAJOR=3, MINOR=0 and PATCH=9.
#                       With OpenSSL 1.1.1u, MAJOR=1, MINOR=1, FIX=1 and
#                       PATCH=t.
# PRE_RELEASE_TAG, BUILD_METADATA, RELEASE_DATE, SHLIB_VERSION
#                       Supplemental state data found in the version file.
#
# _PRE_RELEASE_TAG, _BUILD_METADATA
#                       Computed variants of PRE_RELEASE_TAG and BUILD_METADATA,
#                       with added markup suitable for version numbers in text
#                       form.
#
# SERIES                The current release series.  It is computed from
#                       MAJOR, MINOR and (possibly) FIX
# VERSION               The current version number.  It is computed from
#                       MAJOR, MINOR, (possibly) FIX and PATCH
# FULL_VERSION          Like VERSION, but with metadata (PRE_RELEASE_TAG,
#                       BUILD_METADATA) added
#
# TYPE                  The state the source is in.  It may have an empty value
#                       for released source, or 'dev' for "in development".
#
# PRE_LABEL             May be "alpha" or "beta" to signify an ongoing series
#                       of alpha or beta releases.
# PRE_NUM               A pre-release counter for the alpha and beta release
#                       series, but isn't necessarily strictly tied to the
#                       prerelease label.
#
# Scripts loading this file are not allowed to manipulate these variables
# directly.  They must use next_release_state(), found in release-state-fn.sh.

get_version () {
    ### Reset all variables we defined
    # VERSION_FILE is the version file used
    VERSION_FILE=

    # These are the variables possibly extracted from the version file
    MAJOR=
    MINOR=
    FIX=
    PATCH=
    PRE_RELEASE_TAG=
    BUILD_METADATA=
    RELEASE_DATE=
    SHLIB_VERSION=

    # These are computed from extracted variables
    SERIES=
    VERSION=
    FULL_VERSION=
    TYPE=
    PRE_LABEL=
    PRE_NUM=
    _PRE_RELEASE_TAG=
    _BUILD_METADATA=

    RELEASE_FILES=

    # Detect possible version files.
    # OpenSSL 3.0 and on use VERSION.dat.
    # OpenSSL 1.1.y use include/openssl/opensslv.h
    # OpenSSL 1.0.y (as well as OpenSSL 0.x.y) use crypto/opensslv.h
    for vf in VERSION.dat include/openssl/opensslv.h crypto/opensslv.h; do
        if [ -n "$(git ls-files $vf)" ]; then
            VERSION_FILE=$vf
            break
        fi
    done

    case "$VERSION_FILE" in
        VERSION.dat )
            # The base version data is simply there in VERSION.dat,
            # All we need is to evaluate that file like a shell script.
            eval $(git cat-file blob HEAD:"$VERSION_FILE")

            if [ -n "$PRE_RELEASE_TAG" ]; then
                _PRE_RELEASE_TAG="-${PRE_RELEASE_TAG}"
            fi
            if [ -n "$BUILD_METADATA" ]; then
                _BUILD_METADATA="+${BUILD_METADATA}"
            fi

            SERIES="$MAJOR.$MINOR"
            VERSION="$MAJOR.$MINOR.$PATCH"
            FULL_VERSION="$VERSION$_PRE_RELEASE_TAG$_BUILD_METADATA"
            TYPE=$( echo "$PRE_RELEASE_TAG" \
                        | sed -E \
                              -e 's|^dev$|dev|' \
                              -e 's|^alpha([0-9]+)(-(dev))?$|\3|' \
                              -e 's|^beta([0-9]+)(-(dev))?$|\3|' )
            PRE_LABEL=$( echo "$PRE_RELEASE_TAG" \
                             | sed -E \
                                   -e 's|^dev$||' \
                                   -e 's|^alpha([0-9]+)(-(dev))?$|alpha|' \
                                   -e 's|^beta([0-9]+)(-(dev))?$|beta|' )
            PRE_NUM=$( echo "$PRE_RELEASE_TAG" \
                           | sed -E \
                                 -e 's|^dev$|0|' \
                                 -e 's|^alpha([0-9]+)(-(dev))?$|\1|' \
                                 -e 's|^beta([0-9]+)(-(dev))?$|\1|' )
            RELEASE_FILES='CHANGES.md;NEWS.md'
            ;;
        */opensslv.h )
            # opensslv.h is a bit more difficult to get version data from,
            # as it involves find the C macro definition for it, and calculate
            # the version number from hex digits, having the following meaning:
            #
            # 0xMNNFFPPSL
            #
            # For M = MAJOR, NN = MINOR, FF = FIX, PP = PATCH, S = STATE
            #
            # S has one of the values 0 for development, 1 to e for betas
            # 1 to 14, and f for release.  Because the versions using this
            # scheme are all already released, and this scheme is otherwise
            # abandonned, we only care about the state numbers 0 and f.
            
            # Extract the base version numbers by converting the macro
            # definition of OPENSSL_VERSION_NUMBER into a small shell script
            # that defines appropriate shell variables.  It turns out the
            # perl is the better processor for this sort of thing.
            local version_extractor='
if (m|^[[:space:]]*#[[:space:]]*define[[:space:]]+OPENSSL_VERSION_NUMBER[[:space:]]+0x([[:xdigit:]])([[:xdigit:]]{2})([[:xdigit:]]{2})([[:xdigit:]]{2})([[:xdigit:]])L$|) {
    my $PP = hex($4);
    my $letter_PP = "";
    while ($PP > 25) {
        $letter_PP .= "z";
        $PP -= 25;
    }
    if ($PP > 0) {
        $letter_PP .= chr($PP + ord("a") - 1);
    }
    my $S = hex($5);
    my $tag_S = $S == 0 ? "dev" : "";

    print "MAJOR=",hex($1),"\n";
    print "MINOR=",hex($2),"\n";
    print "FIX=",hex($3),"\n";
    print "PATCH=",$letter_PP,"\n";
    print "PRE_RELEASE_TAG=$tag_S\n";
} elsif (m|^[[:space:]]*#[[:space:]]*define[[:space:]]+SHLIB_VERSION_NUMBER[[:space:]]+"([^"]*)"$|) {
    print "SHLIB_VERSION=$1\n";
}
'
            eval $(git cat-file blob HEAD:"$VERSION_FILE" \
                       | perl -n -e "$version_extractor" )

            # Additional data that's default or computed from the version
            # number data.
            if [ "$MINOR" -eq 0 ]; then
                # 1.0.x
                SHLIB_VERSION="$MAJOR.$MINOR.0"
            else
                # 1.1.x
                SHLIB_VERSION="$MAJOR.$MINOR"
            fi

            if [ -n "$PRE_RELEASE_TAG" ]; then
                _PRE_RELEASE_TAG="-${PRE_RELEASE_TAG}"
            fi

            SERIES="$MAJOR.$MINOR.$FIX"
            VERSION="$MAJOR.$MINOR.$FIX$PATCH"
            FULL_VERSION="$VERSION$_PRE_RELEASE_TAG"
            TYPE=$PRE_RELEASE_TAG
            PRE_LABEL=
            PRE_NUM=0

            if [ -n "$(git ls-files openssl.spec)" ]; then
                # 1.0.x
                RELEASE_FILES='README;CHANGES;NEWS;openssl.spec'
            else
                # 1.1.x
                RELEASE_FILES='README;CHANGES;NEWS'
            fi
            ;;
        * )
            ;;
    esac
}

fixup_version () {
    local new_label="$1"

    case "$new_label" in
        alpha | beta )
            if [ "$new_label" != "$PRE_LABEL" ]; then
                PRE_LABEL="$new_label"
                PRE_NUM=1
            elif [ "$TYPE" = 'dev' ]; then
                PRE_NUM=$(expr $PRE_NUM + 1)
            fi
            ;;
        final | '' )
            if [ "$TYPE" = 'dev' ]; then
                case "$VERSION_FILE" in
                    VERSION.dat )
                        PATCH=$(expr $PATCH + 1)
                        ;;
                    */opensslv.h )
                        local -A patch_transitions
                        patch_transitions=(
                            [_]=a  [_a]=b [_b]=c [_c]=d [_d]=e [_e]=f
                            [_f]=g [_g]=h [_h]=i [_i]=j [_j]=k [_k]=l
                            [_l]=m [_m]=n [_n]=o [_o]=p [_p]=q [_q]=r
                            [_r]=s [_s]=t [_t]=u [_u]=v [_v]=w [_w]=x
                            [_x]=y [_y]=za
                        )
                        PATCH=$( eval set -- "$(echo $PATCH | sed -E -e 's|^(z*)([a-y]?)$|"\1" "\2"|')"
                                 echo $1${patch_transitions[_$2]} )
                        ;;
                esac
            fi
            PRE_LABEL=
            PRE_NUM=0
            ;;
        minor )
            if [ "$TYPE" = 'dev' ]; then
                case "$VERSION_FILE" in
                    VERSION.dat )
                        MINOR=$(expr $MINOR + 1)
                        PATCH=0
                        ;;
                    */opensslv.h )
                        # Minor release updated the FIX number
                        FIX=$(expr $FIX + 1)
                        PATCH=
                        ;;
                esac
            fi
            PRE_LABEL=
            PRE_NUM=0
            ;;
    esac

    case "$TYPE+$PRE_LABEL+$PRE_NUM" in
        *++* )
            PRE_RELEASE_TAG="$TYPE"
            ;;
        dev+* )
            PRE_RELEASE_TAG="$PRE_LABEL$PRE_NUM-dev"
            ;;
        +* )
            PRE_RELEASE_TAG="$PRE_LABEL$PRE_NUM"
            ;;
    esac

    _PRE_RELEASE_TAG=
    if [ -n "$PRE_RELEASE_TAG" ]; then
        _PRE_RELEASE_TAG="-${PRE_RELEASE_TAG}"
    fi

    case "$VERSION_FILE" in
        VERSION.dat )
            SERIES="$MAJOR.$MINOR"
            VERSION="$SERIES.$PATCH"
            FULL_VERSION="$VERSION$_PRE_RELEASE_TAG$_BUILD_METADATA"
            ;;
        */opensslv.h )
            SERIES="$MAJOR.$MINOR.$FIX"
            VERSION="$SERIES$PATCH"
            FULL_VERSION="$VERSION$_PRE_RELEASE_TAG"
            ;;
    esac
}

set_version () {
    case "$VERSION_FILE" in
        VERSION.dat )
            cat > "$VERSION_FILE" <<EOF
MAJOR=$MAJOR
MINOR=$MINOR
PATCH=$PATCH
PRE_RELEASE_TAG=$PRE_RELEASE_TAG
BUILD_METADATA=$BUILD_METADATA
RELEASE_DATE="$RELEASE_DATE"
SHLIB_VERSION=$SHLIB_VERSION
EOF
            ;;
        */opensslv.h )
            local version_updater='
BEGIN {
    my $TYPE="'"$TYPE"'";
    my $MAJOR='"$MAJOR"';
    my $MINOR='"$MINOR"';
    my $FIX='"$FIX"';
    my $PATCH="'"$PATCH"'";

    $PATCH =~ m|^(z)*(.)$|;
    my $PP = length($1) * 25 + ord($2) - ord("a") + 1;

    our $version_number = sprintf("%x%02x%02x%02x%x",
                                  $MAJOR, $MINOR, $FIX, $PP,
                                  $TYPE eq "dev" ? 0 : 0xf);
    our $version_text = sprintf("%d.%d.%d%s", $MAJOR, $MINOR, $FIX, $PATCH);
    our $version_tag="'"$_PRE_RELEASE_TAG"'";
    our $release_date="'"$RELEASE_DATE"'";
    our $shlib_version="'"$SHLIB_VERSION"'";

    $release_date = "xx XXX xxxx" unless ($release_date);
}

s|^([[:space:]]*#[[:space:]]*define[[:space:]]+OPENSSL_VERSION_NUMBER[[:space:]]+0x)[[:xdigit:]]+L$|$1${version_number}L|;
s|^([[:space:]]*#[[:space:]]*define[[:space:]]+OPENSSL_VERSION_TEXT[[:space:]]+)"OpenSSL \d+\.\d+\.\dz*[a-y]?(-fips)?(-dev)?  [^"]+"$|$1"OpenSSL ${version_text}$2${version_tag}  $release_date"|;
s|^([[:space:]]*#[[:space:]]*define[[:space:]]+SHLIB_VERSION_NUMBER[[:space:]]+)"[^"]*"$|$1"${shlib_version}"|;
'
            perl -pi -e "$version_updater" "$VERSION_FILE"
            ;;
    esac
}

std_branch_name () {
    case "$VERSION_FILE" in
        VERSION.dat )
            echo "openssl-${SERIES}"
            ;;
        */opensslv.h )
            echo "OpenSSL_${SERIES//./_}-stable"
            ;;
    esac
}

std_tag_name () {
    case "$VERSION_FILE" in
        VERSION.dat )
            echo "openssl-$FULL_VERSION"
            ;;
        */opensslv.h )
            echo "OpenSSL_${VERSION//./_}"
            ;;
    esac
}
