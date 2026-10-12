# cast-dial-notes

## Casting to and from YouTube without Google: field notes

Practical notes for developers building **Google Cast senders/receivers** or **DIAL receivers**, especially in the de-Googled
Android world (microG, patched YouTube clients, alternative TV apps). Everything here was verified in October 2026 against
real hardware and decompiled apps. It focuses on what is **not** already covered by existing open implementations
(pychromecast, node-castv2, VLC, openscreen) or Google's public docs.

Source tags: `[apk]` decompiled app (YouTube 21.20.405 / Cast SDK 22.3.2, Google Play services 24.23.35 and 26.37.37),
`[capture]` observed on the wire or in logcat, `[ref]` an open reference implementation.

Tested with: classic Chromecast (cast firmware 1.56), Chromecast with Google TV (Android 14, cast 3.72), Samsung phone with
Android 13 running official Play services and microG side by side, Android 15 emulators.

---

## 1. Which route reaches which TV

| You want… | Use | Works with official YouTube + Play services? |
|---|---|---|
| A **sender** (phone/desktop) to a real Chromecast | Cast v2 (CASTV2) | — (you are the sender) |
| A **receiver** that official YouTube can cast to | **DIAL** + YouTube Lounge API | **Yes**, no Google certificate needed |
| A **receiver** that speaks Cast v2 | CASTV2 receiver | **No**: official senders require a Google-signed device certificate (see §3.3). Only senders that skip verification (microG, pychromecast) connect. |

The most useful finding: **a TV app can appear in the cast list of the stock YouTube app via DIAL**, exactly like Samsung/LG
smart TVs do, without any Chromecast or Google certificate. See §5.

---

## 2. Discovery

### 2.1 Cast: mDNS `_googlecast._tcp`
TXT keys and how Play services interprets them `[apk]` (only `id` is required):

| Key | Meaning |
|---|---|
| `id` | device id (32 hex); instance name is usually `<model>-<id>` |
| `fn` | friendly name (fallback: instance name) |
| `md` | model name (`Eureka`/`Chromekey` are rewritten to `Chromecast`) |
| `ve` | device version; mDNS subtype matching only from `ve >= 4` |
| `ca` | capability bits, see below |
| `st` | `0` = idle, anything else treated as busy |
| `rs` | receiver status text (shown as route description) |
| `ic` | icon path on HTTP port 8008 |
| `bs`, `cd`, `nf`, `rm`, `wp`, `ct`, `rr` | hotspot BSSID, cloud device id, remote-control-notification state, metrics id, wake-up port, two undetermined |

`ca` bits used by Play services `[apk]`: `1` video out, `4` audio out (audio-only = 4 without 1), `32` static group,
`64` dynamic group, `128` speaker pair, `2048`/`4096` volume control capabilities. A Chromecast with Google TV advertises `465413`.

### 2.2 DIAL: SSDP
The YouTube app searches with `M-SEARCH`, `ST: urn:dial-multiscreen-org:service:dial:1`, `MX: 1` to `239.255.255.250:1900`
`[apk]` (class `DialDeviceFinder`). It requires the response to carry that exact `ST` and a usable `LOCATION`, then fetches the
UPnP device description (namespace `urn:schemas-upnp-org:device-1-0`) and **requires exactly one `Application-URL` response
header** on it. Chromecasts answer DIAL too.

---

## 3. CASTV2 details that are hard to find elsewhere

### 3.1 What a real Android sender sends `[apk]`
Virtual connection `CONNECT` from Play services:
```json
{"type":"CONNECT","origin":{"package":"<caller>"},
 "userAgent":"Android CastSDK,<gmsVersion>,<MODEL>,<PRODUCT>,<RELEASE>",
 "senderInfo":{"sdkType":1,"version":"<gmsVersion>","platform":1,"systemVersion":"<RELEASE>","model":"<MODEL>","connectionType":2},
 "protocolVersion":3}
```
`protocolVersion: 3` enables message chunking (`continued`/`remaining_length` fields on `CastMessage`). Max serialized message 65536 bytes.

`LAUNCH` includes `language` and **`supportedAppTypes: ["WEB","ANDROID_TV"]`** when the app allows native Android TV receivers.
YouTube sets that (`androidReceiverCompatible: true`, `language: "nl-NL"` in our capture `[capture]`).

Heartbeat: a `PING` every 10 s cycle on `urn:x-cast:com.google.cast.tp.heartbeat`; no traffic for one cycle → disconnect (status 2256).

### 3.2 Android TV receivers report a different app id
A Google TV runs the **native** YouTube app instead of the web receiver and reports it like this `[capture]`:
```json
{"appId":"2C6A6E3D","appType":"ANDROID_TV","universalAppId":"233637DE","displayName":"YouTube", ...}
```
A sender that launched `233637DE` must match **`appId` OR `universalAppId`**, otherwise it thinks the app is not running
(this broke microG's implementation with error 2005). Play services also reports the universal id back to the app and sets
`ApplicationMetadata.type` from `appType` `[apk]`.

### 3.3 Device authentication: why third-party receivers can't be reached by official senders
`[apk]` Play services, for normal LAN devices:
- **TLS**: accepts any server certificate as long as the chain has length 1 and the certificate expires **within 2 days**
  (no CA check). The certificate is just a key for the next step.
- **deviceauth** (`urn:x-cast:com.google.cast.tp.deviceauth`, binary `DeviceAuthMessage`): sender sends a 16-byte nonce
  (reused for a day); the receiver must return a signature over **nonce ‖ TLS peer certificate DER**, made with a key whose
  certificate chains to Google's built-in Eureka/Cast Root CAs, plus a CRL. Any failure closes the socket with status
  2277–2293 and the app shows "untrusted device".
- A hidden setting `com.google.android.gms.cast.SETTINGS_KEY_CAST_BYPASS_DEVICE_AUTH` skips the check, but it is not user-reachable.

`[capture]` A Chromecast with Google TV whose secure key storage is broken returns an **empty** `AuthResponse` (no signature,
no certificate). Official senders then fail with **2278** ("empty certificate chain") and YouTube shows "untrusted device,
possibly outdated firmware". The device's own logs show `CastCertError::ERR_CERTS_MISSING` / "No private key". A healthy
Chromecast returns a 256-byte signature, leaf certificate and one intermediate. Quick probe: send an `AuthChallenge` and look
at the response sizes ([`tools/cast-sniffer/probe_auth.py`](tools/cast-sniffer/probe_auth.py)).

### 3.4 Device quirk: cast receiver stops answering mDNS
`[capture]` On a Chromecast with Google TV the cast service's UDP 5353 socket can stop being read (receive queue full, drops
increasing). The device then disappears from every cast list while TCP 8009 still works. Restarting the cast service fixes it:
```
adb shell am force-stop com.google.android.apps.mediashell
adb shell am startservice -n com.google.android.apps.mediashell/.CastReceiverService
```

---

## 4. The YouTube cast session

### 4.1 Over Cast `[capture]`
1. `LAUNCH 233637DE` (see §3.1).
2. Sender registers `urn:x-cast:com.google.youtube.mdx` and sends `{"type":"getMdxSessionStatus"}`.
3. Receiver answers (and broadcasts) `{"type":"mdxSessionStatus","data":{"screenId":"<64 hex>","deviceId":"<uuid>"}}`.
4. From here the phone controls playback through the **YouTube Lounge API** (YouTube's servers), not over the LAN.
   The receiver still broadcasts `MEDIA_STATUS` on `urn:x-cast:com.google.cast.media`, and the phone's play/pause buttons send
   `PAUSE`/`PLAY` there too. `QUEUE_GET_ITEM_IDS` is answered with `INVALID_REQUEST` by the web receiver (harmless).
5. "Disconnect" in the app leaves the receiver playing; only "Stop casting" sends `STOP`.

Ads on the TV come from the receiver app, so ad-blocking patches on the phone don't affect a Cast session.

### 4.2 Lounge API endpoints a TV ("screen") uses
All on `https://www.youtube.com/api/lounge/` `[ref]` (SmartTube MediaServiceCore, yt-cast-receiver) `[capture]`:

| Endpoint | Purpose |
|---|---|
| `GET pairing/generate_screen_id` | new screen id (plain text) |
| `POST pairing/get_lounge_token_batch` `screen_ids=…` | lounge token per screen |
| `POST pairing/get_pairing_code?ctx=pair` | TV-generated code shown on screen ("Link with TV code") |
| `POST pairing/register_pairing_code` `access_type=permanent&app=…&pairing_code=…&screen_id=…&screen_name=…&device_id=…` | register a **sender-generated** code (DIAL), returns 200 with empty body |
| `bc/bind?…` | the long-poll channel that carries `loungeStatus`, `remoteConnected`, `setPlaylist`, `play`, `pause`, … |

---

## 5. DIAL receiver for the YouTube app (works with official YouTube)

`[apk]` + `[capture]` (stock YouTube 21.40 on Play services, patched YouTube 21.20):

1. Answer the SSDP search (§2.2) with `LOCATION: http://<ip>:<port>/<description>.xml`, `ST: urn:dial-multiscreen-org:service:dial:1`,
   `USN: uuid:<id>::urn:dial-multiscreen-org:service:dial:1`.
2. Serve the device description with header `Application-URL: http://<ip>:<port>/apps/`:
   ```xml
   <root xmlns="urn:schemas-upnp-org:device-1-0"><specVersion><major>1</major><minor>0</minor></specVersion>
     <device><deviceType>urn:dial-multiscreen-org:device:dial:1</deviceType><friendlyName>Living room</friendlyName>
       <manufacturer>…</manufacturer><modelName>…</modelName><UDN>uuid:…</UDN></device></root>
   ```
3. Serve `GET /apps/YouTube` (the phone polls it about every 10 s while the cast dialog is open):
   ```xml
   <service xmlns="urn:dial-multiscreen-org:schemas:dial" dialVer="1.7">
     <name>YouTube</name><options allowStop="false"/><state>stopped</state></service>
   ```
4. On cast the phone sends `POST /apps/YouTube` with `Origin: package:com.google.android.youtube`,
   `Content-Type: text/plain; charset="utf-8"` and body `pairingCode=<code>&theme=cl&dialLaunch=watch` (`browse` when no video
   is open). Answer `201 Created` with a `Location` header.
5. Call `register_pairing_code` (§4.2) for your screen id. The phone then joins your lounge: you receive `loungeStatus` →
   `remoteConnected` → `setPlaylist` on your bind channel.

Measured timing from tap to `setPlaylist`: ~3.3 s, of which ~2.3 s is the Lounge round trip through YouTube's servers.
That is inherent to DIAL/Lounge; a real Chromecast is faster because the video id arrives over the LAN.

Android notes: hold a `WifiManager.MulticastLock` (`CHANGE_WIFI_MULTICAST_STATE`) while listening on 1900; bind the
`MulticastSocket` with `SO_REUSEADDR` because the Chromecast's own cast service also listens there; bringing your activity to
the front from a background service needs the overlay permission on Android 10+.

A complete open implementation: SmartTube `DialServer` (PR [yuliskov/SmartTube#6324](https://github.com/yuliskov/SmartTube/pull/6324)) + `registerPairingCode` ([yuliskov/MediaServiceCore#55](https://github.com/yuliskov/MediaServiceCore/pull/55)).

---

## 6. Android Cast SDK ↔ Play services contract (for microG and other GmsCore implementations)

Condensed; full tables in [`spec/youtube-cast-sdk-client.md`](spec/youtube-cast-sdk-client.md), [`spec/youtube-cast-sdk-client-21.20-delta.md`](spec/youtube-cast-sdk-client-21.20-delta.md), [`spec/play-services-cast-service.md`](spec/play-services-cast-service.md).

- **Bind**: action `com.google.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE`, service id **161** (`CAST_API`,
  `ICastService`: feature flags, int maps, settings) and id **10** (`CAST`, `ICastDeviceController`). Modern apps use the
  **connectionless** path: extras contain `connectionless_client_record_id` and `EXTRA_CAST_DEVICE`, the listener is registered
  later via a transaction, not in the extras.
- **Handshake** (wire transaction codes = AIDL id + 1): `addListener` (18) → `connect` (17) → wait for listener
  `onConnectedWithResult(0)` (14) → `launchApplication` (13) / `joinApplication` (14) → listener `onApplicationConnected` (2).
  Controller codes 1 disconnect, 4 leave, 5 stop, 7 setVolume, 9 sendMessage, 11/12 register/unregister namespace;
  listener 5 text message, 10/11 send result, 12 application status, 13 device status, 15 connection suspended.
- **SDK 22.3+**: every controller/ICastService call appends an `ApiMetadata` parcel (servers must not enforce "no data left");
  a new `connectWithOptions` (21) is only used when ICastService returns `FLAG_ENABLE_CONNECT_WITH_OPTIONS=true`.
- **Requested features** (all version 1): `client_side_logging, cxless_client_minimal, cxless_caf_control, module_flag_control,
  discovery_hint_supply, relay_casting_set_active_account, analytics_proto_enum_translation, integer_to_integer_map,
  relay_casting_set_remote_casting_mode, get_relay_access_token, get_cast_settings, set_bundle_setting, get_client_updated_info,
  device_suggestions, cxless_connect_with_options`.
- **cast-framework**: apps load the dynamite module `com.google.android.gms.cast.framework.dynamite` and drive
  `CastContext`/`SessionManager`/`CastSession` through it. Route extras: `com.google.android.gms.cast.EXTRA_CAST_DEVICE`
  (CastDevice parcelable), `EXTRA_RUNNING_RECEIVER_APP_ID`. Control category format:
  `com.google.android.gms.cast.CATEGORY_CAST/<appId>/<%-encoded namespaces>/<flags>`, YouTube uses `…/233637DE///ALLOW_IPV6`.
- MediaRouter unselect reason `UNSELECT_REASON_DISCONNECTED` (1) is what you get when the user **switches** receivers: end the
  session, don't suspend it.

Working implementation: [microg/GmsCore#3845](https://github.com/microg/GmsCore/pull/3845) plus fixes in [woahwhattheheck/GmsCore#16](https://github.com/woahwhattheheck/GmsCore/pull/16).

---

## 7. Patched YouTube (ReVanced / Morphe) and Cast

The "GmsCore support" patch makes `DefaultCastSdkClient.onComplete(Task<CastContext>)` return immediately (fingerprint:
string `"Error fetching CastContext."`) so the app doesn't crash on GmsCore builds without Cast. Side effect: YouTube's
cast client **never registers its session listener**, so even with a working Cast implementation the session connects and then
nothing happens (no `youtube.mdx` handshake; the receiver closes after ~20 s). The patches also force "Hide cast button".
Proposed option: [MorpheApp/morphe-patches#3709](https://github.com/MorpheApp/morphe-patches/pull/3709). DIAL (§5) is unaffected by this patch.

On Android 13+ MediaRouter2 merges route providers, so with official Play services **and** microG installed every Chromecast
appears twice; which provider handles a cast is visible in logcat (`CastMediaRouteProvider`, `CDC` tags).

---

## 8. Tooling that helped

- **SSDP/DIAL probe** ([`tools/dial-probe/dial_probe.py`](tools/dial-probe/dial_probe.py), stdlib Python): advertises a DIAL device and logs what the phone sends,
  including registering the pairing code. Fastest way to check whether a given YouTube build lists DIAL devices.
- **CASTV2 sniffer** ([`tools/cast-sniffer`](tools/cast-sniffer), pychromecast-based): `discover` (TXT records), `watch` (join as second sender and log
  broadcasts), `youtube-ref` (reference YouTube sender), `proxy` (TLS man-in-the-middle; official senders abort at deviceauth, so
  only useful for senders that don't verify).
- **Frida** on an emulator (attach by process name, use frida-server over TCP + `adb forward` when USB attach is flaky) to see
  why obfuscated app code takes a branch. `dexdump -d` on the APK settles disagreements between jadx output and runtime behaviour.
- **Android emulator caveats**: give it `-dns-server 1.1.1.1,8.8.8.8` if DNS fails; on API 35 the emulator *does* receive LAN
  mDNS answers via `NsdManager`, but Google Play services' own Cast scanner finds nothing in the emulator.

---

## Repository layout

- [`spec/`](spec): the detailed notes behind this guide (Cast SDK client side, Play services service side, CASTV2 captures,
  discovery, DIAL, YouTube MDX). Facts are tagged with their source; obfuscated class names refer to the stated app versions.
- [`tools/dial-probe`](tools/dial-probe): minimal DIAL receiver that logs what YouTube sends (Python standard library only).
- [`tools/cast-sniffer`](tools/cast-sniffer): CASTV2 discovery, watcher, reference YouTube sender, TLS proxy and deviceauth probe.

Corrections and additions are welcome as issues or pull requests; these details change with every YouTube and Play services release.
No decompiled code is reproduced here, only observed behaviour.

See also the [microG gap map](https://rleroi.github.io/microg-gap-map/): which other Play services features microG still lacks.
