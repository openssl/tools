all: randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall pemread

clean:
	rm libperf.a *.o randbytes handshake sslnew newrawkey rsasign x509storeissuer providerdoall pemread

#-Wl,-rpath,$(TARGET_OSSL_LIBRARY_PATH)

CPPFLAGS += -I$(TARGET_OSSL_INCLUDE_PATH) -I.
CFLAGS += -pthread
LDFLAGS += -L$(TARGET_OSSL_LIBRARY_PATH) -L.

libperf.a: perflib/*.c perflib/*.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c perflib/*.c
	ar rcs libperf.a *.o

randbytes:	randbytes.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o randbytes randbytes.c -lperf -lcrypto

handshake: handshake.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o handshake handshake.c -lperf -lcrypto -lssl

sslnew: sslnew.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o sslnew sslnew.c -lperf -lcrypto -lssl

newrawkey:	newrawkey.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o newrawkey newrawkey.c -lperf -lcrypto

rsasign: rsasign.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o rsasign rsasign.c -lperf -lcrypto

x509storeissuer: x509storeissuer.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o x509storeissuer x509storeissuer.c -lperf -lcrypto

providerdoall:	providerdoall.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o providerdoall providerdoall.c -lperf -lcrypto

pemread:	pemread.c libperf.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o pemread pemread.c -lperf -lcrypto
