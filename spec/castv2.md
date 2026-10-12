# CASTV2 transport and core namespaces

Framing `[reference-impl]` (pychromecast `socket_client.py`, matches #3845 `CastChannel.kt` `[pr]`): TLS to port 8009; each frame = 4-byte big-endian length + protobuf `CastMessage { protocol_version=CASTV2_1_0, source_id, destination_id, namespace, payload_type STRING|BINARY, payload_utf8 | payload_binary }`.

Namespaces seen so far `[capture]`:
- `urn:x-cast:com.google.cast.tp.connection` — `{"type":"CONNECT", ...}` / `{"type":"CLOSE"}` per virtual connection (sender-N ↔ receiver-0 or a transportId).
- `urn:x-cast:com.google.cast.receiver` — `GET_STATUS` → `RECEIVER_STATUS`.
- `urn:x-cast:com.google.cast.tp.heartbeat` — PING/PONG (not logged by default).
- `urn:x-cast:com.google.cast.tp.deviceauth` — binary `DeviceAuthMessage` (challenge/response/error), proto in pychromecast `cast_channel_pb2` and #3845 `cast_channel.proto`.

## Minimal exchange captured against the Google TV (idle, 2026-10-12) `[capture]`
```
tx sender-0→receiver-0 tp.connection {"type":"CONNECT","origin":{},"userAgent":"PyChromecast","senderInfo":{...}}
tx sender-0→receiver-0 receiver      {"type":"GET_STATUS","requestId":1}
rx receiver-0→sender-0 receiver      {"requestId":1,"type":"RECEIVER_STATUS","status":{"userEq":{},"volume":{"controlType":"fixed","level":1.0,"muted":false,"stepInterval":0.04}}}
tx sender-0→receiver-0 tp.connection {"type":"CLOSE","origin":{}}
```
Note: no `applications` array while idle; `volume.controlType` is `fixed` on this Google TV (HDMI-CEC volume), unlike `attenuation`/`master` on audio devices. microG's route must not assume variable volume. `[capture]`

No deviceauth was exercised (pychromecast skips it). The real sequence with an official sender is pending (`tools/cast-sniffer` proxy mode).

## Device authentication `[capture]` `[apk]`
- Official Play Services (26.37.37) sends `AuthChallenge{sender_nonce: 16 bytes (reused for a day), signature_algorithm: 1}` and
  requires `AuthResponse{signature, client_auth_certificate, intermediate_certificate[]}`; empty chain → internal code 6 →
  `Cast socket status code 2278`, connection closed, UI "Niet vertrouwd apparaat" (`play-services-cast-service.md` §5.3).
- Healthy Chromecast Bedroom: `signature 256 B, leaf cert 1252 B(b64), 1 intermediate, CRL 3687 B`. Broken Google TV
  "Living room": `signature 0 B, no cert, CRL 3687 B` even after a clean reboot (2026-10-12). Probe tool: `tools/cast-sniffer/probe_auth.py <host>`.
- Chromecast 1.56 answers `GET_STATUS` with `applications[{appId:"E8C28D3C", displayName:"Backdrop", appType:"WEB", universalAppId:"E8C28D3C"}]` when idle.
