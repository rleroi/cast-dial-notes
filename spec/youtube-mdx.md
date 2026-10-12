# YouTube cast session: `urn:x-cast:com.google.youtube.mdx` and the Lounge handoff

Sources: `[capture]` official sender (test phone, Play Services 26.37.37, YouTube 21.40.163) → Chromecast Bedroom
(cast fw 1.56.291998), 2026-10-12 14:08, observed from a second sender (`tools/cast-sniffer` watch mode, so only
broadcasts and receiver-side status are visible; sender-specific replies are not) + phone logcat
. `[apk]` = decompiled YouTube / Play Services. `[reference-impl]` = pychromecast.

## 1. Session establishment as done by the official sender `[capture]` `[apk]`
1. Play Services opens TLS to the receiver, runs deviceauth (verified; see `castv2.md`), virtual `CONNECT` to `receiver-0`.
   logcat: `Connected to device. rejoinedApp: true`.
2. YouTube (via cast-framework) calls `launchApplicationWithOptions: 233637DE LaunchOptions(relaunchIfRunning=false, language=nl-NL, androidReceiverCompatible: true)`.
   → the CASTV2 `LAUNCH` therefore carries `appId 233637DE`, `language nl-NL`, `supportedAppTypes ["WEB","ANDROID_TV"]` `[apk]` (payload shape from Play Services code, values from logcat).
3. Receiver status seen by the second sender: Backdrop `E8C28D3C` → empty → `{"appId":"233637DE","displayName":"YouTube","statusText":"YouTube","appType":"WEB","universalAppId":"233637DE", namespaces: media, system?, cac?, youtube.mdx (4 total)}`.
4. ~3 s later Play Services reports `onApplicationConnected: applicationId 233637DE, name YouTube, namespaces.count 4`, sessionId = receiver `sessionId`.
   On a Google TV the same app shows up as `appId 2C6A6E3D`, `appType ANDROID_TV`, `universalAppId 233637DE`; match on `universalAppId` too, see the README §3.2.
5. YouTube receiver broadcasts on `urn:x-cast:com.google.youtube.mdx`:
   `{"type":"mdxSessionStatus","data":{"screenId":"<64 hex>","deviceId":"<uuid>"}}` — this is the answer to the sender's
   `{"type":"getMdxSessionStatus"}` `[apk]` (YouTube `akwh.java`/`akes.java`) and is also pushed to every connected sender.
6. From here playback is driven over the **YouTube Lounge API** (cloud), not CASTV2: the second sender only sees the
   receiver's `MEDIA_STATUS` broadcasts change (BUFFERING → PLAYING, PAUSED on pause, seeks as BUFFERING at new `currentTime`).
   No `LOAD`/`PLAY`/`PAUSE` arrives on `urn:x-cast:com.google.cast.media` from the phone.
7. Volume: hardware volume keys produced `multizone` namespace broadcasts (`urn:x-cast:com.google.cast.multizone`,
   `{"device":{"capabilities":196613,"deviceId":"<uuid>","name":"Bedroom","volume":{"level":0.95,"muted":false}}}`)
   and `RECEIVER_STATUS` updates every 0.05 step.
8. "Disconnect" in the YouTube app closes the sender's connection only; the receiver app keeps playing (`[capture]`, user-observed).
   "Stop casting" would send `STOP`.

## 2. What microG must do for YouTube (derived)
- Launch/join matching must accept `universalAppId`.
- Pass `LaunchOptions.language` and `androidReceiverCompatible` through to `LAUNCH` (#3845 does `[pr]`).
- Forward `youtube.mdx` text messages both ways unchanged; register the namespace on `registerNamespace`.
- Report `ApplicationMetadata{appId=233637DE (universal), name, namespaces[4], type}` and `sessionId`/`transportId` from the receiver status.
- Nothing Lounge-specific: the phone talks to the Lounge API itself once it has `screenId`.

## 3. Reference sender sequence (pychromecast `YouTubeController`) `[reference-impl]`
See  (git-ignored). Sender sends `LAUNCH 233637DE`, then on the app transport
`getMdxSessionStatus`, receives `mdxSessionStatus{screenId,deviceId}`, then uses the Lounge API with that screenId
(`pychromecast/controllers/youtube.py`, `youtube_session`).
