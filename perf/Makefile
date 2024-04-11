all: randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall pemread pkeyread

clean:
	rm libperf.a *.o randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall pemread pkeyread

#-Wl,-rpath,$(TARGET_OSSL_LIBRARY_PATH)

CFLAGS += -I$(TARGET_OSSL_INCLUDE_PATH) -I.
LDFLAGS += -L$(TARGET_OSSL_LIBRARY_PATH) -L.

libperf.a: perflib/*.c perflib/*.h
	gcc $(CFLAGS) -c perflib/*.c
	ar rcs libperf.a *.o

randbytes:	randbytes.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o randbytes randbytes.c -lperf -lcrypto

handshake: handshake.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o handshake handshake.c -lperf -lcrypto -lssl

sslnew: sslnew.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o sslnew sslnew.c -lperf -lcrypto -lssl

newrawkey:	newrawkey.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o newrawkey newrawkey.c -lperf -lcrypto

rsasign: rsasign.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o rsasign rsasign.c -lperf -lcrypto

x509storeissuer: x509storeissuer.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o x509storeissuer x509storeissuer.c -lperf -lcrypto

providerdoall:	providerdoall.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o providerdoall providerdoall.c -lperf -lcrypto

pemread:	pemread.c libperf.a
	gcc $(CFLAGS) $(LDFLAGS) -o pemread pemread.c -lperf -lcrypto

pkeyread:	pkeyread.c libperf.a
	$(CC) $(CFLAGS) -pthread $(LDFLAGS) -o pkeyread pkeyread.c -lperf -lcrypto
