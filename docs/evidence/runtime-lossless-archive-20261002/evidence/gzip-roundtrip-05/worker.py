from pathlib import Path
import hashlib,json,resource,struct,sys,time,zlib

source=Path(sys.argv[1]); output=Path(sys.argv[2]); started=time.monotonic()
maximum=4*1024**3; block=1024**2
with source.open('rb') as stream:
    prefix=stream.read(10)
    assert prefix[:3]==b'\x1f\x8b\x08' and prefix[3]==8, 'closed gzip header flags'
    header=bytearray(prefix)
    while header[-1]!=0 or len(header)==10:
        data=stream.read(1);assert data and len(header)<4096
        header+=data
    stream.seek(-8,2); trailer=stream.read(8)
compressed_hash=hashlib.sha256(); restored_hash=hashlib.sha256(header); tar_hash=hashlib.sha256()
decompressor=zlib.decompressobj(31); compressor=zlib.compressobj(1,zlib.DEFLATED,-15)
compressed_size=0; restored_size=len(header); tar_size=0
with source.open('rb') as stream:
    for raw in iter(lambda:stream.read(block),b''):
        compressed_hash.update(raw);compressed_size+=len(raw)
        pending=raw
        while pending:
            decoded=decompressor.decompress(pending,block);pending=decompressor.unconsumed_tail
            if decompressor.unused_data: raise ValueError('multiple gzip members or trailing bytes unsupported')
            tar_size+=len(decoded)
            if tar_size>maximum:raise ValueError('decoded stream bound exceeded')
            tar_hash.update(decoded);packed=compressor.compress(decoded)
            restored_hash.update(packed);restored_size+=len(packed)
    assert decompressor.eof,'truncated gzip'
packed=compressor.flush();restored_hash.update(packed);restored_size+=len(packed)
restored_hash.update(trailer);restored_size+=len(trailer)
usage=resource.getrusage(resource.RUSAGE_SELF)
result=dict(schema='runtime-gzip-exact-stream-roundtrip@1',source=str(source),original_sha256=compressed_hash.hexdigest(),
    original_bytes=compressed_size,reconstructed_sha256=restored_hash.hexdigest(),reconstructed_bytes=restored_size,
    exact=compressed_hash.digest()==restored_hash.digest() and compressed_size==restored_size,
    decoded_tar_bytes=tar_size,decoded_tar_sha256=tar_hash.hexdigest(),decoded_cap_bytes=maximum,
    gzip_header_hex=header.hex(),gzip_trailer_hex=trailer.hex(),gzip_mtime=struct.unpack('<I',header[4:8])[0],
    deflate=dict(level=1,wbits=-15,memLevel=8,strategy=zlib.Z_DEFAULT_STRATEGY),
    python=sys.version,zlib_compile=zlib.ZLIB_VERSION,zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,
    seconds=time.monotonic()-started,peak_rss_bytes=usage.ru_maxrss*1024,
    cpu_user_seconds=usage.ru_utime,cpu_system_seconds=usage.ru_stime,
    originals_modified=False,expanded_tar_or_reconstructed_gzip_written=False)
output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'exact':result['exact'],'seconds':result['seconds'],'tar_bytes':tar_size,'peak_rss_bytes':result['peak_rss_bytes']}),flush=True)
if not result['exact']:sys.exit(2)
