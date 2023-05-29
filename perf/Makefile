all: randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall

clean:
	rm libperf.a *.o randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall

libperf.a: perflib/*.c perflib/*.h
	gcc -I$(TARGET_OSSL_INCLUDE_PATH) -I. -c perflib/*.c
	ar rcs libperf.a *.o

randbytes:	randbytes.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o randbytes randbytes.c -lperf -lcrypto

handshake: handshake.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o handshake handshake.c -lperf -lcrypto -lssl

sslnew: sslnew.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o sslnew sslnew.c -lperf -lcrypto -lssl

newrawkey:	newrawkey.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o newrawkey newrawkey.c -lperf -lcrypto

rsasign: rsasign.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o rsasign rsasign.c -lperf -lcrypto

x509storeissuer: x509storeissuer.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o x509storeissuer x509storeissuer.c -lperf -lcrypto

providerdoall:	providerdoall.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o providerdoall providerdoall.c -lperf -lcrypto
