# Exact frozen CI failure and isolated repair

Frozen source 1aa67ba42a667d8c3f214a80bf31b297d269c58e was ordinarily pushed to dev/f1-foundation. Standard Windows Server CI [37526795142](https://github.com/T1doo/Sim2Act/actions/runs/37526795142) finished FAILURE: 876 passed, 13 failed, 5 skipped; smoke and owned cleanup passed. Protected Edge step was SKIPPED, hence no new native protocol pixels were captured or reviewed. This is distinct from the independently reproduced prior AT05 child empty-argv startup race, and does not reinterpret older failures.

Two concrete fixture causes: blanket connect interception catches the Windows asyncio Proactor socketpair self-pipe; default Git text conversion changes manifest-pinned LF material bytes to CRLF. Narrow fix authenticates only the exact stdlib fallback frame/socket/loopback listener; direct connections and real HTTPTransport remain denied. Attributes preserve imported raw bytes. No oracle/gold/manifest or browser security conditions changed.

Local focused: 19 passed, 1 explicit PG skip, plus independent socket oracle 5 passed. New bounded evidence exporter includes only protocol-results.json and protocol-desktop/protocol-narrow PNGs from the owned protocol subdirectory; it excludes DB/profile/info/credentials. Export means transport availability, not pixel review. Frozen 1aa did not have this exporter correction.

This repair is local only. A second Windows CI/push requires a new parent decision; this package does not claim native Proactor or Edge verification.
