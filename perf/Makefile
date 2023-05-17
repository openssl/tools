all: randbytes

clean:
	rm libperf.a *.o randbytes

libperf.a: perflib/*.c perflib/*.h
	gcc -I$(TARGET_OSSL_INCLUDE_PATH) -I. -c perflib/*.c
	ar rcs libperf.a *.o

randbytes:	randbytes.c libperf.a
	gcc -L$(TARGET_OSSL_LIBRARY_PATH) -L. -I$(TARGET_OSSL_INCLUDE_PATH) -I. -o randbytes randbytes.c -lperf -lcrypto
