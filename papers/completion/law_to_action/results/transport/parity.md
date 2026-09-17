# LA-013 actual transport parity and content-retrieval qualification

This record qualifies stdio, loopback HTTP, and loopback libp2p carriage of the
selected `SupervisorPreInvocationEnforcement.authorize_and_delegate` route.
It is **not** a scored A3 or A4 benchmark.

## Network versus in-process modes

- `stdio`: **local-process**. Anonymous pipes. `actual_network=false`.
- `http`: **local-network**. `127.0.0.1` plaintext HTTP. `wan=false`.
- `libp2p`: **local-network**. TCP + Noise + Yamux, protocol `/mcp+p2p/1.0.0`, loopback multiaddrs. `wan=false`.
- `in-process` and kit `handle_stream_message`: **in-process**. Not libp2p network evidence.

## Authoritative environment

- Python: `/usr/bin/python3.12` 3.12.3
- PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- libp2p: 0.7.0 compatible=True
- IPFS daemon: available=False binary=None

## Selected route

ENFORCE around `BoundedExportHandler.export_json`. Kit `AuthorizationGate` / `MCPServer.tools/call` is not the selected safety claim.

## Qualified transport processes

| Transport | network_mode | actual_network | wan | in_process | protocol | security | pid/peer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `stdio` | local-process | False | False | False | `jsonrpc-2.0-ndjson` | anonymous-pipes | 411 |
| `http` | local-network | True | False | False | `jsonrpc-2.0-http` | plaintext-http | 412 |
| `libp2p` | local-network | True | False | False | `/mcp+p2p/1.0.0` | noise | 12D3KooWFe1GYtKjoNTMmQCN5zdcNbD1gmz9KuWz2cJMF2chiRwD |

## Semantic parity (identical tools/call requests)

| Case | stdio | HTTP | libp2p | effects | pass |
| --- | --- | --- | --- | --- | --- |
| `allow` | allow | allow | allow | 1 | True |
| `deny` | deny | deny | deny | 0 | True |
| `unknown` | unknown | unknown | unknown | 0 | True |
| `wrong-audience` | deny | deny | deny | 0 | True |
| `replay` | deny | deny | deny | 0 | True |

## Content retrieval: integrity versus availability

- Public CID (`bafkreifc7gtlqbt76e2k3ybugfm62vknho5dmdqd72nnxtrfernw2r3sl4`) was rehashed under CIDv1/raw/sha2-256/base32.
- Public availability is **local-only**. No kubo/ipfs daemon served the CID.
- Private CID (`bafkreify5eh7qh3w353olic4em7paq7epmc4w5ruvvkezvn6kcpf2qgs5q`) was computed in memory. `private_bytes_published=false`.

| Job | integrity | availability | published | pass |
| --- | --- | --- | --- | --- |
| `stdio-content-public` | True | local-process-store | False | True |
| `stdio-content-private` | False | not-published | False | True |
| `http-content-public` | True | local-process-store | False | True |
| `http-content-private` | False | not-published | False | True |
| `libp2p-content-public` | True | local-process-store | False | True |
| `libp2p-content-private` | False | not-published | False | True |
| `http-cid-get-public` | True | local-http | False | True |
| `http-cid-get-private-absent` | False | not-published | False | True |
| `ipfs-daemon-unavailable` | None | ipfs-daemon-absent | False | True |

## Failures and narrowed claims

No case-level assertion failures. Optional WAN/publication claims remain unrun.

- Wide-area libp2p, DHT, mDNS, AutoNAT, relay, and holepunch were disabled and are not claimed.
- Kit `serve_p2p` does not listen; its in-process framer is not network evidence.
- Private legal/security source bytes were not added to any content store or public output.
- This is qualification evidence, not a scored forbidden-effect rate.
