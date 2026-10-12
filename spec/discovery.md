# Cast discovery (mDNS / DNS-SD)

Service type: `_googlecast._tcp.local.` `[capture]` (seen from the Mac with pychromecast/zeroconf and macOS `dns-sd -B`).

## Observed instance: Chromecast with Google TV "Living room" (2026-10-12) `[capture]`

Instance name: `Chromecast-<device-id>._googlecast._tcp.local.` (= "Chromecast-" + `id`), host <ip>, port 8009.
Cast firmware per `GET http://<ip>:8008/setup/eureka_info`: `cast_build_revision` 3.72.446070.

TXT record:

| key | value | meaning (observed / `[reference-impl]` pychromecast) |
|---|---|---|
| `id` | `<device-id>` | receiver id, 32 hex; also the mDNS instance suffix |
| `cd` | `<32 hex>` | 32 hex, unknown purpose ("certificate digest"? not verified) |
| `rm` | `` | empty |
| `ve` | `05` | protocol/device version |
| `md` | `Chromecast` | model name |
| `ic` | `/setup/icon.png` | icon path on port 8008 |
| `fn` | `"Living room"` | friendly name |
| `ca` | `465413` | capability bitmask (decimal); microG #3845 masks it with `CAPABILITY_MASK` and reads VIDEO_OUT/AUDIO_OUT/MULTIZONE_GROUP bits `[pr]` |
| `st` | `0` | status (0 = idle) |
| `bs` | `<bssid>` | matches `hotspot_bssid` in eureka_info |
| `nf` | `3` | unknown |
| `rs` | `` | receiver status text (empty when idle) |

Other receivers on the LAN (friendly name / model / host): Bedroom / Chromecast / <ip>; "an audio receiver" / an audio receiver / <ip> (audio only). `[capture]`

## Behaviour notes
- The Google TV stopped announcing after a reboot because `cast_shell`'s UDP 5353 receive buffer filled up (drops climbing); restarting `com.google.android.apps.mediashell` / `CastReceiverService` fixed it. `[capture]` (the tester, device-side inspection)
- Android receivers do not answer unicast mDNS queries sent to port 5353; use multicast browsing only. `[capture]`

## What a sender needs from this record (for microG)
`id`, `fn`, `md`, `ca`, `st`, host, port. #3845's provider treats only `id` as mandatory. `[pr]` Verify against the Play Services provider in `cast-framework-interfaces.md` (Play Services side) when decompiled.
