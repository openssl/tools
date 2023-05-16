#include <stdlib.h>
#include <stdio.h>
#include <openssl/rand.h>
#include <openssl/crypto.h>
#include "perflib/threads.h"
#include "perflib/time.h"

#define NUM_CALLS_PER_BLOCK         100
#define NUM_CALL_BLOCKS_PER_THREAD  100
#define NUM_CALLS_PER_THREAD        (NUM_CALLS_PER_BLOCK * NUM_CALL_BLOCKS_PER_THREAD)

int err = 0;

void do_randbytes(void)
{
    int i;
    unsigned char buf[32];

    for (i = 0; i < NUM_CALLS_PER_THREAD; i++)
        if (!RAND_bytes(buf, sizeof(buf)))
            err = 1;
}

int main(int argc, char *argv[])
{
    int threadcount, i;
    thread_t *threads;
    OSSL_TIME start, end;
    uint64_t us;
    double avcalltime;

    if (argc != 2) {
        printf("Usage: randbytes threadcount\n");
        return EXIT_FAILURE;
    }

    threadcount = atoi(argv[1]);
    if (threadcount < 1) {
        printf("threadcount must be > 0\n");
        return EXIT_FAILURE;
    }

    threads = OPENSSL_malloc(sizeof(*threads) * threadcount);
    if (threads == NULL)
    {
        printf("malloc failure\n");
        return EXIT_FAILURE;
    }

    start = ossl_time_now();

    for (i = 0; i < threadcount; i++)
        perflib_run_thread(&threads[i], do_randbytes);

    for (i = 0; i < threadcount; i++)
        perflib_wait_for_thread(threads[i]);

    end = ossl_time_now();
    OPENSSL_free(threads);

    if (err) {
        printf("Error during test\n");
        return EXIT_FAILURE;
    }

    us = ossl_time2us(ossl_time_subtract(end, start));

    avcalltime = (double)us / (NUM_CALL_BLOCKS_PER_THREAD * threadcount);

    printf("Average time per %d RAND_bytes() calls: %lfus\n",
           NUM_CALLS_PER_BLOCK, avcalltime);

    return EXIT_SUCCESS;
}
