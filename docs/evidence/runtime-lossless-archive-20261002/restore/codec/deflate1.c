#include <stdio.h>
#include <string.h>
#include <zlib.h>

/* A bounded raw-DEFLATE level-1 filter. Linked statically for local archival. */
int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--version") == 0) {
        printf("raw-deflate-level1 zlib-compile=%s zlib-runtime=%s\n", ZLIB_VERSION, zlibVersion());
        return 0;
    }
    if (argc != 1) return 2;
    unsigned char input[65536], output[65536];
    z_stream stream = {0};
    if (deflateInit2(&stream, 1, Z_DEFLATED, -15, 8, Z_DEFAULT_STRATEGY) != Z_OK) return 3;
    int done = 0;
    while (!done) {
        size_t count = fread(input, 1, sizeof(input), stdin);
        if (ferror(stdin)) { deflateEnd(&stream); return 4; }
        int flush = feof(stdin) ? Z_FINISH : Z_NO_FLUSH;
        stream.next_in = input;
        stream.avail_in = (unsigned int) count;
        do {
            stream.next_out = output;
            stream.avail_out = sizeof(output);
            int status = deflate(&stream, flush);
            if (status != Z_OK && status != Z_STREAM_END) { deflateEnd(&stream); return 5; }
            size_t size = sizeof(output) - stream.avail_out;
            if (fwrite(output, 1, size, stdout) != size) { deflateEnd(&stream); return 6; }
            done = status == Z_STREAM_END;
        } while (stream.avail_out == 0 || (flush == Z_FINISH && !done));
        if (stream.avail_in != 0) { deflateEnd(&stream); return 7; }
    }
    deflateEnd(&stream);
    return fflush(stdout) == 0 ? 0 : 8;
}
