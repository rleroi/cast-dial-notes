# DIAL discovery and launch in the YouTube app (alternative to Cast for Part B)

Source: YouTube 21.20.405 decompile `[apk]`. To be confirmed with a live DIAL receiver `[capture]`.

- Discovery (`defpackage/akfz.java`, logger tag `MDX.DialDeviceFinder`): SSDP `M-SEARCH * HTTP/1.1` to 239.255.255.250:1900 with
  `ST: urn:dial-multiscreen-org:service:dial:1`, `MX: 1`. Accepts responses with that `ST` and a usable `LOCATION`; fetches the UPnP
  device description (namespace `urn:schemas-upnp-org:device-1-0`) and requires exactly one `Application-URL` response header.
- Launch (`defpackage/akge.java`): POST to the DIAL application URL with headers `Content-Type: text/plain; charset="utf-8"`,
  `Origin: package:com.google.android.youtube`, body `pairingCode=<code>&theme=cl&dialLaunch=watch|browse` plus extra parameters.
  The TV app is expected to register that pairing code with the YouTube Lounge service; the phone then joins the Lounge session.
  Screen types in MDX include a DIAL screen (`DialScreen` in `akcy`, `aknd`, `aksy`).
- Why it matters: DIAL has no device authentication. A TV app that answers SSDP + device description + the YouTube DIAL app endpoint
  appears in the cast list of **any** YouTube sender (official Play Services, our microG, iOS), unlike Cast which requires a Google-signed
  device certificate for official senders.

## Verified on hardware (2026-10-12) `[capture]` (`tools/dial-probe/dial_probe.py`, log `tools/dial-probe/probe.log`)
Phone test phone on the LAN, probe on a Mac advertising "DIAL test (Mac)":
- Both **Morphe YouTube 21.20.405** (UA reports `com.google.android.youtube/21.20.405`) and **stock YouTube 21.40.163 with official Play Services**
  list the DIAL device in the cast dialog. Sequence: `M-SEARCH` (ST dial) → `GET /ssdp/device-desc.xml` → `GET /apps/YouTube` (polled every
  ~10 s while the dialog is open) → on selection `POST /apps/YouTube` with headers `Origin: package:com.google.android.youtube`,
  `Content-Type: text/plain; charset="utf-8"` and body `pairingCode=<code>&theme=cl&dialLaunch=browse|watch` (`watch` when a video is open).
- Receiver answers `201 Created` + `Location`, then `POST https://www.youtube.com/api/lounge/pairing/register_pairing_code` with
  `access_type=permanent, app=lb-v4, pairing_code, screen_id, screen_name, device_id` → `200` (empty body). The screen id came from
  `GET …/pairing/generate_screen_id`. Cross-checked with yt-cast-receiver `[reference-impl]` (no license: facts only, no code reused).
- **Conclusion: a DIAL receiver is reachable from official YouTube senders; no Google device certificate is involved.** Next step is the
  Lounge bind on the screen side, which SmartTube already implements for "Link with TV code".

## SmartTube DIAL receiver: first implementation verified (2026-10-12) `[capture]`
SmartTube beta 32.67 debug (`org.smarttube.beta`, branch `dial-receiver` in SmartTube + MediaServiceCore) on the Chromecast with Google TV:
`DialServer` (SSDP on UDP 1900 + HTTP on 8090: `/dd.xml`, `/apps/YouTube`), started by `RemoteControlService` when
"Show in YouTube cast list (DIAL)" is on (independent of the "Remote control" switch). On launch it calls
`LoungeService.registerPairingCode` (`POST …/pairing/register_pairing_code` with SmartTube's own screen id) and SmartTube's existing
lounge listener receives `loungeStatus` → `remoteConnected` (stock YouTube `android-phone-21.40.163`) → `setPlaylist` → opens the video.
Works from stock YouTube (official Play Services) and Morphe YouTube. Timing from tap: register +0.1 s, lounge `remoteConnected` +2.3 s
(server relay), `setPlaylist` +3.3 s, player init +3.9 s, then SmartTube's normal stream loading.
