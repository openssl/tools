#! /bin/bash
#
# Run in a directory for a gost engine build.
# Two subdirectories will be created:
#
#    gost-engine	a checkout of https://github.com/gost-engine/engine.git
#    openssl		a checkout of https://github.com/openssl/openssl.git
#
# Required ubuntu packages to run this script:
#
#    build-essential
#    cmake
#    perl
#    git

if [ -d openssl ]; then
    (cd openssl; git pull --rebase)
else
    git clone -b OpenSSL_1_1_0-stable --depth 1 --single-branch \
	https://github.com/openssl/openssl.git openssl
fi

if [ -d gost-engine ]; then
    (cd gost-engine; git pull --rebase)
else
    git clone https://github.com/gost-engine/engine.git gost-engine
fi

OPENSSL_PREFIX=$(pwd)/openssl/_install
(
    cd openssl
    ./config --prefix=$OPENSSL_PREFIX \
	&& make -j8 build_libs \
	&& make install_dev
) && (
    cd gost-engine
    cmake -DOPENSSL_ROOT_DIR=$OPENSSL_PREFIX \
          -DCMAKE_MODULE_LINKER_FLAGS='-Wl,--enable-new-dtags' \
          .
    make
)
