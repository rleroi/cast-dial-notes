# Cast SDK ↔ Play Services interfaces

Sources: `[apk]` decompiled YouTube 19.17.42 / 21.20.405 (stock + Morphe) and Play Services 24.23.35; `[capture]` logcat of Morphe YouTube 21.20.405 against MicroG-RE + PR #3845 on an Android 15 emulator (2026-10-12); `[pr]` microG PRs. Detailed per-side tables are merged in from `youtube-cast-sdk-client.md` and `play-services-cast-service.md` once complete.

## 1. Live bind observation `[capture]`

Morphe YouTube 21.20.405 (package `app.morphe.android.youtube`) against `app.revanced.android.gms` (MicroG-RE with microg/GmsCore#3845):

- Bind intent action: `app.revanced.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE` (the Morphe-rewired action; the stock `com.google.android.gms.cast.service.…` string is also present in the dex but was not used for this bind).
- `GetServiceRequest`: service id **`CAST_API` (161)**, `gmsVersion=262105000`, `scopes=[]`, `extras=Bundle[{}]`, `defaultFeatures=[]`, `supportsConnectionInfo=true`.
- `apiFeatures` requested (all version 1):
  `client_side_logging`, `cxless_client_minimal`, `cxless_caf_control`, `module_flag_control`, `discovery_hint_supply`, `relay_casting_set_active_account`, `analytics_proto_enum_translation`, `integer_to_integer_map`, `relay_casting_set_remote_casting_mode`, `get_relay_access_token`, `get_cast_settings`, `set_bundle_setting`, `get_client_updated_info`, `device_suggestions`, `cxless_connect_with_options`.
  → #3845's fixed `CAST_SERVICE_FEATURES` list (`module_flag_control`, `analytics_proto_enum_translation`, `integer_to_integer_map`, …) must be checked against this; `cxless_connect_with_options` and `cxless_caf_control` are not in it. `[pr]` Whether the SDK gates anything on them is an open question for the APK analysis.
- Dynamite: `createModuleContext for com.google.android.gms.cast.framework.dynamite at version 1` succeeded (ModuleDescriptor from #3845).
- `CastOptions` parcel from YouTube carries **field ids 17, 18, 19, 20 unknown to microG** (`SafeParcel: Unknown field id 17..20 in com.google.android.gms.cast.framework.CastOptions, skipping`). Newer SDK fields; semantics to recover from `[apk]`.
- Discovery: `CastMediaRouteProvider` found the three LAN receivers through `NsdManager` (Android 15 `MdnsDiscoveryManager`), routes were added via `MediaRouterCallbackImpl.onRouteAdded`, `SessionManagerImpl` moved `NO_DEVICES_AVAILABLE → NOT_CONNECTED`. So the A1 done-criterion (devices listed) is reachable with #3845; UI confirmation pending.
- The `CAST` (10) device-controller bind had not happened yet at this point (no route selected).

## 2. Detailed recovered interfaces
- Client side (YouTube 19.17.42 Cast SDK 21.5.0): `youtube-cast-sdk-client.md` `[apk]`
- Server side (Play Services 24.23.35): `play-services-cast-service.md` `[apk]`
- YouTube 21.20.405 delta: see `youtube-cast-sdk-client-21.20-delta.md`.

## 3. Cross-check: wire codes (client 19.17.42 `[apk]` vs GMS 24.23.35 `[apk]` vs PR #3845 AIDL id+1 `[pr]`)
| wire | GMS server meaning | client uses | #3845 |
|---:|---|---|---|
| 1 | disconnect | yes | ✓ |
| 2 / 3 | launch / join without options (legacy) | no | ✗ (not needed) |
| 4 | leaveApplication | yes | ✓ |
| 5 | stopApplication(sessionId) | yes | ✓ |
| 6 | requestStatus | — | ✓ |
| 7 | setVolume(double,double,bool) | yes | ✓ |
| 8 | setMute(bool,double,bool) | — | ✓ |
| 9 | sendMessage(ns,msg,reqId) | yes | ✓ |
| 10 | sendBinaryMessage | — | ✓ |
| 11 / 12 | register/unregisterNamespace | yes | ✓ |
| 13 / 14 | launch(LaunchOptions) / join(JoinOptions) | yes | ✓ |
| 15 | sendText with destinationId (Google-signed callers only) | no | ✗ |
| 16 | equalizer | no | ✗ |
| 17 | connect (cxless) | yes | ✓ |
| 18 | addListener/registerListener (cxless) | yes | ✓ |
| 19 | removeListener | yes | ✓ |
| 20 | getClientInfo(IBundleCallback, String[]) | not seen | ✗ |

Listener (wire): 1 onDisconnected, 2 onApplicationConnected, 3 onApplicationConnectionFailed, 4 legacy status (unused), 5 text, 6 binary, 7 leaveResult, 8 stopResult, 9 onApplicationDisconnected, 10 sendFailed, 11 sendEnqueued/success, 12 ApplicationStatus, 13 DeviceStatus, 14 onConnectedWithResult(0 | 2300 | error), 15 onConnectionSuspended. #3845 implements 1–3, 5–15 at matching ids. ✓

Conclusion: the AIDL numbering in #3845 is correct; #3802's "off by one" was wrong, as its author later agreed. `[apk]` `[pr]`
