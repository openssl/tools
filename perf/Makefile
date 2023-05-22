all: randbytes handshake

clean:
	rm libperf.a *.o randbytes handshake

libperf.a: perflib/*.c perflib/*.h
	gcc -I$(TARGET_OSSL_INCLUDE_PATH) -I. -c perflib/*.c
	ar rcs libperf.a *.o

randbytes:	randbytes.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o randbytes randbytes.c -lperf -lcrypto

handshake: handshake.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o handshake handshake.c -lperf -lcrypto -lssl