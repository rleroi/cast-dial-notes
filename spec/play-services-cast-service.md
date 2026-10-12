# GMS Cast API — service side, as implemented in Google Play Services 24.23.35

Source: jadx decompilation of `com.google.android.gms` 24.23.35 (242335038, Android 15 Play emulator image).
All paths are relative to the jadx `sources/` root. Every statement is tagged `[apk]` and derived from the
cited file; nothing was taken from documentation or memory. Where decompilation failed or the data is not in
Java code, the item is marked **not determined**.

---

## 1. Service registration (CastChimeraService / GMS service broker)

### 1.1 Service ids and bind action
- [apk] `com/google/android/gms/cast/service/CastChimeraService.java` constructor:
  `super(new int[]{10, 161}, new String[]{"com.google.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE", "...BIND_CAST_DEVICE_CONTROLLER_SERVICE"}, epki.a, 3, 10)`.
  Both service ids **10** (CAST) and **161** (CAST_API) are served by the same Chimera bound service under the same
  bind action `com.google.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE`.
- [apk] `defpackage/boer.java` (base ApiService) `onBind`: returns `null` if the intent action is not in the list;
  otherwise returns `new boeq(this)` (the `IGmsServiceBroker` stub, `defpackage/boeq.java`). `boeq.b(...)` calls
  `boer.hP(bundle, iBinder)` when the GetServiceRequest carries a non-null IBinder, then delegates to `bofs.b(...)`.
- [apk] `CastChimeraService.hP(Bundle, IBinder)`: if the broker request carries the callback binder, it is put into
  the extras as `bundle.putParcelable("listener", new BinderWrapper(iBinder))` (class loader set to CastDevice's).
- Other cast-related services (remote display, firstparty, rcn) exist as separate packages
  (`com/google/android/gms/cast/remote_display`, `firstparty`, `rcn`) but are not part of CastChimeraService and
  were not analysed; their service ids: **not determined**.

### 1.2 Dispatch in `CastChimeraService.kF(boez, GetServiceRequest)` [apk]
(Dispatch logic summarised below; decompiled code not reproduced.)
- id 161 → returns `aiur` (ICastService implementation, section 4) with status 0.
- id 10 → reads the extras bundle `getServiceRequest.i`:
  - `CastDevice.d(bundle)` = `bundle.getParcelable("com.google.android.gms.cast.EXTRA_CAST_DEVICE")`
    (`com/google/android/gms/cast/CastDevice.java` `d()`/`i()`). If null/invalid → `boezVar.a(10, null)` (status 10).
  - `boolean z  = bundle.getBoolean("com.google.android.gms.cast.EXTRA_CAST_FRAMEWORK_NOTIFICATION_ENABLED")`
  - `boolean z2 = bundle.getBoolean("com.google.android.gms.cast.EXTRA_CAST_REMOTE_CONTROL_NOTIFICATION_ENABLED")`
  - `boolean z3 = bundle.getBoolean("com.google.android.gms.cast.EXTRA_CAST_ALWAYS_FOLLOW_SESSION_ENABLED")`
  - `String string = bundle.getString("connectionless_client_record_id")`
  - `long j = bundle.getLong("com.google.android.gms.cast.EXTRA_CAST_FLAGS", 0L)`; if the calling package is in the
    Phenotype list `ftni.a.a().g()` then `j |= 8`.
  - `str = getServiceRequest.f` (calling package name); `i2 = getServiceRequest.e` (client GMS version).
  - If `connectionless_client_record_id != null` ("cxless" path, used by the Cast framework/CAF):
    if `!ftkp.a.a().c()` (`CxlessServiceStub__enabled`, default true in `defpackage/ftkr.java`) → `boezVar.a(3, null)`;
    else creates `new aivn(...)` (section 2.2) which itself calls `boezVar.c(this)` immediately (status 0, no
    connection yet). No `listener` extra is used in this path; the listener is registered later via controller code 18.
  - Else (classic path): reads `BinderWrapper bw = bundle.getParcelable("listener")`, converts to
    `ICastDeviceControllerListener` (`aims`; proxy `aimq`). Null → `boezVar.a(10, null)`.
    Reads `last_application_id` and `last_session_id` strings. Creates `new aiwf(...)` (section 2.1), which
    immediately starts connecting to the device; the GetService callback is only answered after the CASTV2 connection
    completes (see 3.2).
- [apk] `EXTRA_USE_ROUTE_CONNECTION`: no occurrence in `CastChimeraService.java`, `aiwf.java` or `aivn.java` — **not read by this service**.

### 1.3 Status codes returned via the broker callback (onPostInitComplete) [apk]
`defpackage/boez.java`: `a(int, Bundle)` → `bofx.c(status, null, bundle)`; `c(bofl)` → status 0 with the stub binder;
`b(int, IBinder, Bundle)` → arbitrary status with binder. `defpackage/bofx.java` `f()` forwards to
`IGmsCallbacks.onPostInitCompleteWithConnectionInfo` when `getServiceRequest.m` is set, else `onPostInitComplete(status, binder, bundle)`.
- `aiwf.iN(boolean rejoined)`: `rejoined ? boezVar.c(this) /*0*/ : boezVar.b(2300, this, null)`.
  Client side (`defpackage/aimg.java` `r()`): 2300 is translated to status 0 plus bundle extra
  `com.google.android.gms.cast.EXTRA_APP_NO_LONGER_RUNNING=true`.
- `aiwf.iO(int)`: connection failure → `boezVar.a(i, null)` where `i = 2301` unless
  `ftjt.e()` (`CastModuleConfigs__service_stub_should_pass_original_error_code`, default true, `defpackage/ftjv.java`)
  and `i != 0`, in which case the original cast status code is passed.
- `aivv.f()` (ConnectToDevice op): if no controller could be created → `boezVar.b(2017, aiwf, null)`.

### 1.4 Feature[] advertised in ConnectionInfo [apk]
- `defpackage/ahsu.java` holds the static `Feature[] n` =
  `client_side_logging(1), cxless_client_minimal(1), cxless_caf_control(1), module_flag_control(1), discovery_hint_supply(1),
  relay_casting_set_active_account(1), analytics_proto_enum_translation(1), integer_to_integer_map(1),
  relay_casting_set_remote_casting_mode(1), get_relay_access_token(1), get_cast_settings(1), set_bundle_setting(1),
  get_client_updated_info(1)` — all version `1L`.
- This array is used **client side**: `defpackage/aimh.java` (`CastClientImplCxless`, service id 10) `f()` returns
  `ahsu.n` and `defpackage/ampk.java` line ~455 puts `f()` into `GetServiceRequest.l` (the "requested features" field).
- Service side, `defpackage/boft.java` (`FeatureCheckPreproc`) `b(GetServiceRequest, ConnectionInfo)`: collects names from
  `getServiceRequest.k` (required) and `.l` (requested), calls `ModuleManager.get(ctx).fetchFeatures(names)`, parses the
  returned proto (`pli`/`plf`: name, version, deprecated flag) and sets `connectionInfo.b = featureArr3`. If any
  *required* (`k`) feature is missing → `ConnectionResult(1)`; if a required version is too old → `ConnectionResult(21)`.
  If both arrays are empty → `connectionInfo.b = new Feature[0]`.
- The Cast module's own feature table (what `fetchFeatures` returns) lives in the Chimera module manifest, not in Java;
  no resources were present in the jadx output → the exact server-side list is **not determined**, but the only Cast
  feature names referenced by the client are the 13 in `ahsu.n` above, and a microG implementation must report at least
  those (all at version 1) for `aimh`/CAF clients to connect without `ConnectionResult(1)`.

---

## 2. ICastDeviceController stub (service side)

Interface descriptor: `com.google.android.gms.cast.internal.ICastDeviceController` (`defpackage/aimo.java`).
All methods are **oneway** on the wire: the client proxy `defpackage/aimn.java` uses `hh(code, parcel)` which is
`transact(code, parcel, null, FLAG_ONEWAY=1)` (`defpackage/oxg.java` `hh`). The stub `aimo.hf` reads the parcel and returns
true without writing a reply. Two implementations exist: `aiwf` (classic, id 10 with `listener` extra) and `aivn`
(cxless). Both validate namespaces with `A()`/`B()`: a message/registration is silently dropped when the namespace is empty,
longer than 128 chars, equals `urn:x-cast:com.google.cast.webrtc` (`aipr.b`), starts with `urn:x-cast:com.google.cast.tp`
(`aizm.g`), or equals `com.google.cast.receiver`, `.receiver.debug`, `.resource`, `.system` (`aizm.b/c/d/f`); `com.google.cast.setup`
(`aizm.e`) and `com.google.cast.multizone` (`aimw.b`) are only allowed for Google-signed callers (`aizt.s`). Namespace constants
are built with `aimk.g(...)` (prefix; see `defpackage/aizm.java`).

| code | params read (Parcel, in order) | aiwf / aiad behaviour [apk] |
|---|---|---|
| 1 | – | `disconnect()`: `aiwf.b()` → `B(true)` → `aiad.c(true)`: sends `CLOSE` on `com.google.cast.tp.connection` to the current app transport id (`aiau.d`) if explicit and connected, then closes socket. Listener gets `onDisconnected` (code 1) from `aiad.F()`. |
| 2 | String appId, bool relaunchIfRunning | deprecated `launchApplication` → builds `LaunchOptions{a=relaunch}` → code 13 path. |
| 3 | String appId, String sessionId | deprecated `joinApplication` → code 14 path with `new JoinOptions()`. |
| 4 | – | `leaveApplication`: `aiad.f()`: if an app is connected → `B(0)` → listener `onApplicationDisconnected(0)` (code 9); else listener `onApplicationLeaveFailed` (code 7, 2001). |
| 5 | String sessionId | `stopApplication`: `aiad.m()` sends `{"requestId":n,"type":"STOP","sessionId":s}` on `com.google.cast.receiver` to `receiver-0`; tracked with `stop` timeout (`receiver_control_channel:request_timeout_ms` = 20000, `defpackage/ftnh.java`). |
| 6 | – | `requestStatus`: `aiad.i()` → `aibo.b()` sends `{"requestId":n,"type":"GET_STATUS"}` on `com.google.cast.receiver`. |
| 7 | double volume, double currentVolume, bool currentMuted | `setVolume`: `aiad.s()`: clamps to [0,1]; sends `{"requestId":n,"type":"SET_VOLUME","volume":{"level":v},"expectedVolume":{"level":cur,"muted":m[,"stepInterval":..]}}`. If device lacks capability bits 6144 (`castDevice.j(6144)` false) the service shows a toast "volume not supported" (`aiwf.y`). |
| 8 | bool mute, double currentVolume, bool currentMuted | `setMute`: `aiad.r()`: `{"type":"SET_VOLUME","volume":{"muted":m},"expectedVolume":{...}}`. |
| 9 | String namespace, String message, long requestId | `sendTextMessage`: `aiad.k()` → `l(ns, msg, id, x())` where `x()` = current session transport id (`aibo.c`). Enqueued in `aiaj` (max queue `max_channel_send_queue_size`=5); if full → listener `onMessageSendFailed(ns,id,2007)` (code 10). On write success listener `onMessageEnqueued(ns,id)` (code 11) [only if message not chunked-continued]. Serialized size > 65536 → `onMessageSendFailed(..,2006)`. IOException → disconnect with 2257. |
| 10 | String namespace, byte[] data, long requestId | `sendBinaryMessage`: `aiad.j()` → `O(ns, bytes, id, x())`. |
| 11 | String namespace | `registerNamespace`: `aiad.h()` adds to set `p` (messages on unregistered namespaces are not forwarded). |
| 12 | String namespace | `unregisterNamespace`: `aiad.n()`. |
| 13 | String appId, LaunchOptions (SafeParcelable) | `launchApplicationWithOptions`: empty appId → listener `onApplicationConnectionFailed(2470)` (code 3). `aiad.e()`→`H()`: if `launchOptions.a` (relaunch) sends LAUNCH immediately; else `aa(appId,"")` = join-if-running, and `v=true` so a LAUNCH is sent after GET_STATUS shows the app is not running. LAUNCH payload: section 5.6. |
| 14 | String appId, String sessionId, JoinOptions | `joinApplicationWithOptions`: non-Google caller forces `joinOptions.a = 0` (STRONG). `aiad.d()` → `aa(appId, sessionId)`: if already connected to that app → listener `onApplicationConnected` (code 2) immediately; else `GET_STATUS` and join on RECEIVER_STATUS; mismatch → `onApplicationConnectionFailed(2053)`. |
| 15 | String namespace, String message, long requestId, String destinationId | `sendTextMessageWithDestinationId`: only for Google-signed callers (`aizt.s`), otherwise ignored. |
| 16 | EqualizerSettings | `setEqualizerSettings`: only if `equalizer_settings_enabled` (default true): sends `{"type":"SET_USER_EQ","userEq":{...}}`. |
| 17 | – | `aiwf.a()` no-op. `aivn.a()` (cxless) = **connect**: `aivd` → `aiaq.b()` opens the CASTV2 socket. |
| 18 | IBinder ICastDeviceControllerListener | `aiwf.iS` no-op (listener came from GetService extras). `aivn.iS` registers the listener (`linkToDeath`). |
| 19 | – | `aiwf.v()` no-op; `aivn.v()` unregisters listener. |
| 20 | IBinder IBundleCallback, String[] keys | `aiwf.x` no-op. `aivn.x`: for key `com.google.android.gms.cast.CLIENT_INFO_PLAYBACK_SESSION_NAME` puts the playback session name; replies via `IBundleCallback.onResult(Bundle)` = transaction 1 (`defpackage/aimm.java`, oneway). |

Notes [apk]:
- `aiwf` constructor (`defpackage/aiwf.java`): links to death of both the broker callback and the listener; then posts
  `aivv` ("ConnectToDevice"): if a controller for this device already exists and is connected → answers GetService
  immediately with status 0 (`f.c(aiwf)`); else `aiad.b()` (connect) or, when `last_application_id` was given,
  `aiad.g(lastAppId, lastSessionId)` (reconnect and rejoin).
- Controller sharing: `ahzo.a(...)`/`aias` cache controllers per device id (`aiat` wrapper for relay/cloud devices).
- `aiwf.binderDied` → `B(false)` (disconnect without CLOSE message).

### 2.2 cxless variant `defpackage/aivn.java` [apk]
Used by CAF (feature `cxless_client_minimal`): the stub is returned immediately in the GetService callback; connection
only starts at code 17, listener set via code 18, and connection results are reported through listener code 14
(`onConnectedWithResult`, see 3.2). It wraps `aiaq` (a sibling controller with the same public API as `aiad`; not analysed
in detail). Flags `j |= 4` ("follow session") when `EXTRA_CAST_ALWAYS_FOLLOW_SESSION_ENABLED` or package listed in
`ftld.f()`.

---

## 3. ICastDeviceControllerListener proxy (what the service calls back)

Descriptor `com.google.android.gms.cast.internal.ICastDeviceControllerListener`. Service-side proxy `defpackage/aimq.java`;
client-side stub `defpackage/aimr.java`. All calls are **oneway** (`oxg.hh`). Parcel: interface token, then:

| code | written | when (service) [apk] |
|---|---|---|
| 1 | int status | `onDisconnected`: `aiwf.iR(i)` after socket close (`aiad.F`): status = pending disconnect code or `aiad.Y(socketError)` (0 for clean; 2250..2275 for socket errors, 2258 unknown). Heartbeat timeout → 2256. Auth failures → 2277..2293 (see 5.3). |
| 2 | ApplicationMetadata (SafeParcelable), String sessionId, String transportId (wire order: metadata, `str`=applicationStatus text? see note), bool wasLaunched | `onApplicationConnected`: `aiad.ab()` → `ahzn.e.iL(metadata, t, s, z)` where `t = ahzi.g` (**statusText**), `s = ahzi.f` (**sessionId**), `z` = launched by this request. So wire order is: metadata, statusText, sessionId, wasLaunched. |
| 3 | int status | `onApplicationConnectionFailed`: `aiad.I(code)`: 2004 (empty appId / NOT_FOUND), 2053 (join mismatch), LAUNCH_ERROR reasons: BAD_PARAMETER 2471, CANCELLED 2472, NOT_ALLOWED 2474 (+toast), CAST_INIT_TIMEOUT 2473, SYSTEM_ERROR 2475, MULTICHANNEL_NOT_CONNECTED 2478, other 2476; INVALID_REQUEST→2001 or 13; launch request timeout (65000 ms `receiver_control_channel:launch_request_timeout_ms`) → 15 (`defpackage/aini.java` `k(15)`); empty appId at launch 2470. |
| 4 | String appStatusText, double volume, bool muted | deprecated `onStatusReceived`; suppressed for new clients (`anjq.a(clientVersion)`). |
| 5 | String namespace, String message | `onTextMessageReceived` (`aiad` → `ahzl.o`). Only for registered namespaces. |
| 6 | String namespace, byte[] data | `onBinaryMessageReceived`. |
| 7 | int (always 2001) | `onApplicationLeaveFailed` (`aiwf.iW`). |
| 8 | int status | `onApplicationStopFailed` (`aiwf.e`). |
| 9 | int status | `onApplicationDisconnected`: `aiad.B(code)`: 0 explicit leave; 2005 when a new app launch replaced running app; 2055 when RECEIVER_STATUS shows session gone and `u` (stop requested) is false, 0 after own STOP. |
| 10 | String namespace, long requestId, int status | `onMessageSendFailed` (2007 queue full, 2006 too large, 2257 network, 2001 invalid). |
| 11 | String namespace, long requestId | `onMessageEnqueued` (after socket write). |
| 12 | ApplicationStatus (SafeParcelable) | `onApplicationStatusChanged` — emitted from `aibo.h` (not decompiled) when RECEIVER_STATUS statusText changes. |
| 13 | DeviceStatus (SafeParcelable) | `onDeviceStatusChanged` — from `aibo.i()` on each RECEIVER_STATUS. |
| 14 | int status | `onConnectedWithResult` — **only in cxless path** (`aivn.iN`): `0` when connected without a rejoined app, `2300` when connected and the previously running app is gone (rejoinedApp=false); `aivn.iO` → failure code (2301 unless original code passthrough enabled). In the classic path (`aiwf`) this method is never called; success is signalled via the GetService callback (1.3). |
| 15 | int status | `onConnectionSuspended` (`aivn.iP`, cxless only). |

### 3.3 SafeParcelable layouts [apk]
- `ApplicationMetadata` (`com/google/android/gms/cast/ApplicationMetadata.java` `writeToParcel`): 2 String appId (`a`),
  3 String name (`b`), 4 (null string list, legacy), 5 String list namespaces (`c`), 6 String senderAppIdentifier (`d`),
  7 Uri senderAppLaunchUrl (`e`), 8 String iconUrl (`f`), 9 String type (`g`, "WEB"/... from `appType`, or `WEB` if
  `universalAppId` present), 10 Boolean senderConnected (`h`), 11 Boolean launchedFromCloud (`i`).
  Filled by `aiad.W(ahzi)` from the RECEIVER_STATUS `applications[0]` object (`defpackage/ahzi.java`): `appId`, `displayName`,
  `iconUrl`, `namespaces[].name`, `universalAppId`, `appType`, `senderApps[]{platform,package,url}` (platform==1 → Android
  package/url), `senderConnected`, `launchedFromCloud`, `sessionId`, `transportId`, `statusText`.
- `DeviceStatus` (`com/google/android/gms/cast/internal/DeviceStatus.java`): 2 double volume level, 3 bool muted,
  4 int activeInputState (`isActiveInput` → 1/0, else -1), 5 ApplicationMetadata (set in `aibo.h`, not decompiled),
  6 int standbyState (`isStandBy` → 1/0, else -1), 7 EqualizerSettings (`userEq.low_shelf/high_shelf`),
  8 double stepInterval (`volume.stepInterval`, only when `step_interval_enabled`; default NaN).
- `ApplicationStatus` (`.../internal/ApplicationStatus.java`): 2 String applicationStatus text.
- `CastDevice` (`com/google/android/gms/cast/CastDevice.java`): 2 deviceId, 3 hostAddress, 4 friendlyName, 5 modelName,
  6 deviceVersion, 7 int servicePort, 8 WebImage list icons, 9 int capabilities, 10 int status, 11 serviceInstanceName,
  12 receiverMetricsId, 13 int rcnEnabledStatus, 14 hotspotBssid, 15 byte[] ipLowestTwoBytes, 16 cloudDeviceId,
  17 bool isCloudOnlyDevice, 18 CastEurekaInfo, 19 Integer wakeupServicePort. `g()` strips a `__cast_nearby__` prefix from
  the id; `j(mask)` = `(capabilities & mask) == mask`.

---

## 4. ICastService (service id 161) — `defpackage/aimu.java` stub, `defpackage/aiur.java` impl [apk]

Descriptor `com.google.android.gms.cast.internal.ICastService`. Replies go through callback binders, never through the
reply parcel (proxy `aimt` is a stub that throws; the client-side proxy with real codes is elsewhere — the stub codes below
are authoritative).

| code | params | implementation (`aiur`) |
|---|---|---|
| 1 | IStatusCallback, String[] deviceIds, String precacheData | deprecated → same as 2 with `list=null`. |
| 2 | IStatusCallback, String[] deviceIds, String precacheData, List<RequestItem> | "BroadcastPrecacheMessageOperation" (`defpackage/aiuq.java`): if no data and no items → `Status(2490)`; if `ftms` flag enabled sends `{"type":"PRECACHE","precacheData":..,"requestItems":[{url,protocolType,initialTime,hlsSegmentFormat}]}` via multicast `239.255.3.22` / or a device connection; else `Status(2491)`. |
| 3 | byte[] | read and ignored. |
| 4 | IStatusCallback | `getCxLessStatus`-style check: `Status(ftkp.d() ? 0 : 2003)` — `CxlessServiceStub__should_caf_use_cxless` default **true** → `Status(0)`. |
| 5 | IBundleCallback, String[] flagNames | module flag control: returns Bundle with, per requested key: `FLAG_CLIENT_SESSION_ANALYTICS_ENABLED` (bool), `FLAG_CLIENT_SESSION_ANALYTICS_MODE` (int 0..3), `FLAG_FIRELOG_UPLOAD_MODE` (long), `FLAG_ANALYTICS_LOGGING_BUCKET_SIZE` (long), `FLAG_CLIENT_FEATURE_USAGE_ANALYTICS_ENABLED` (bool), `FLAG_CLIENT_ANALYTICS_ENABLED` (bool), `FLAG_ANALYTICS_CONSENT_TIMEOUT_SECONDS` (long), `FLAG_OUTPUT_SWITCHER_ENABLED` (bool) — all keys prefixed `com.google.android.gms.cast.`. |
| 6 | IBundleCallback, String[] keys | `k()`: for `com.google.android.gms.cast.DICTIONARY_CAST_STATUS_CODES_TO_APP_SESSION_ERROR` and `..._TO_APP_SESSION_CHANGE_REASON` puts `Serializable` (ImmutableMap<Integer,Integer>) built from fixed tables (e.g. `0→34, 7→2, 15→4, 2000→6, 2002→14, 2003→20, 2004→21, 2300→34, 2301→36, 2250→66 … 2275→91, 2277→7 … 2293→98, 2470→28, 2490..2493→33`; change-reason table `2→12, 1→13, 2154→9, 2155→16, …, 2005→27, 2050→28 … 2055→8, 2310→14, 2016→15, 2019→24, 2020→25, 2021→26, 2022→33`). Full list in `aiur.java` lines 315–494. |
| 7 | IBundleCallback, String[] keys | `j()`: for `com.google.android.gms.cast.MAP_CAST_STATUS_CODES_TO_CAST_REASON_CODES` puts an ImmutableMap<Integer,Integer>: `8→1`; `{0,2300,2002,2154..2161,2005,2050..2055}→2` then overrides `2155→9`, `2005,2050..2055→3`; `2150,2151→4`; `2152,2153→5`; `2250..2258,2262..2275→6`; `15→7`; `2259,2260,7,2276→8`; `2470..2478→10`; `2019..2022→11`; `2420,2422→12`; `2421,2423→13`; `2424..2426→14`; `2427..2430→15`. |
| 8 | IBundleCallback, List<String> settingKeys | `h()`: returns cast settings for allowed keys only: `com.google.android.gms.cast.BUNDLE_KEY_CAST_ENABLED_STATUS`, `SETTINGS_KEY_CAST_NEARBY_TOGGLE_STATE`, `SETTINGS_KEY_CAST_NEARBY_TOGGLE_TIMESTAMP` (via `aizt.c`). |

`IBundleCallback` = `com.google.android.gms.cast.internal.IBundleCallback`, single oneway transaction 1 with a Bundle (`aimm.a`).
`IStatusCallback` = `com.google.android.gms.common.api.internal.IStatusCallback` (`alvj`), transaction 1 `onResult(Status)`.

---

## 5. CASTV2 channel implementation

Core classes: `defpackage/aiad.java` (CastDeviceController), `defpackage/ahym.java` (`CastSocket`, SSLEngine over NIO
`SocketChannel`), `defpackage/aiaj.java` (CastMessage builder/queue), `defpackage/aiau.java` (connection channel),
`defpackage/aibe.java` (device auth), `defpackage/aibh.java` (heartbeat), `defpackage/aibo.java` (receiver control channel),
`defpackage/ahzy.java` (socket listener glue).

### 5.1 TLS socket [apk]
- `ahym.s(name, InetAddress, port)` connects to `CastDevice.g` (servicePort; default 8009 in `defpackage/ahsm.java`, from mDNS SRV port
  `MdnsServiceInfo.g` in `aidt.a`). Connect timeout `H = 5000` ms.
- Two static `SSLContext`s (`ahym.x()`/`y()`), both initialised with a client `KeyManager` `ahzk.a(context)` (self-signed RSA key
  "cast_nearby_client_auth" in AndroidKeyStore, CN=cast_nearby_client_auth) and one of two trust managers:
  - default (`z2 == false`): `defpackage/ahxx.java`: `checkServerTrusted` requires **chain length exactly 1**, calls
    `checkValidity()`, and rejects if `notAfter` is more than 2 days (172800000 ms) in the future
    ("Peer certificate has excessive lifetime"). No CA check at TLS level.
  - strict (`z2 == true`, chosen when `aiwl.e(castDevice)`: device id contains `__cloud_device__` or is a known relay device):
    `defpackage/ahzd.java` validates the chain with PKIX against the two built-in roots in `defpackage/aibf.java`
    (Eureka Root CA, Cast Root CA), revocation disabled.
- `ahym.r()` returns DER of `peerCertificates[0]` after handshake — used as the deviceauth peer certificate.
- Note: for a normal LAN Chromecast (`ahxx`), a receiver certificate with lifetime <= 2 days passes TLS; the real trust
  decision is deviceauth (5.3).

### 5.2 CastMessage framing [apk] (`defpackage/aiaj.java`, proto `defpackage/enif.java`)
`enif` fields: `b`=protocol_version (`enie.CASTV2_1_0`), `c`=source_id, `d`=destination_id, `e`=namespace, `f`=payload_type
(STRING=0 / BINARY=1), `g`=payload_utf8, `h`=payload_binary, `i`=continued (bit 128), `j`=remaining_length (bit 256) — the
last two for message chunking (`MessageChunking__is_enabled` default true). source_id = `"<callingPackage>-<counter>"`
(`aiad` constructor: `String.format("%s-%d", pkg, Q.incrementAndGet())`). Max serialized size 65536
(`aiad.D()`), `max_message_payload_length` flag 65024.

### 5.3 Device authentication (`defpackage/aibe.java`, `ahzy.b()`) [apk]
- Trigger: `ahzy.b()` on socket connected. **Bypass**: if the settings pref
  `com.google.android.gms.cast.SETTINGS_KEY_CAST_BYPASS_DEVICE_AUTH` (read via `aizt.e(ctx)`/`bobw.i`) is true, logs
  "authentication bypassed" and calls `aiad.E(false)` directly (no challenge). Also `aiad.L == true` skips auth.
- Challenge: `DeviceAuthMessage{ challenge: AuthChallenge{ sender_nonce(field 2) = 16 random bytes, signature_algorithm(field 3) = 1 } }`
  (`enhn` fields: `b` = nonce, `c = 1`; `enhs.b` = challenge, bit 1). The nonce is persisted in prefs
  `PREF_CAST_SENDER_NONCE` / `PREF_CAST_SENDER_NONCE_GENERATED_TIME` and regenerated after 1 day (`aibe.j`). No
  `hash_algorithm` field is set in the challenge. Sent as a **binary** message on namespace
  `urn:x-cast:com.google.cast.tp.deviceauth` to `receiver-0`. If the peer cert DER is null → failure 17.
- Response handling `aibe.g(byte[])`: parses `enhs` (DeviceAuthMessage). If `challenge` set → ignored. If `error` (bit 4) →
  result 5 ("error received"). If no `response` (bit 2) → ignored. Otherwise `aibe.c(...)`:
  1. `bArr2 == null` (no peer cert) → 17.
  2. If `device_auth:enforce_sender_nonce` (`ftku.a`, default **false**) is enabled, the response's `sender_nonce` (`enhr.f`)
     must equal the sent nonce else 10 ("response malformed"). By default this check is skipped.
  3. Builds cert path from `client_auth_certificate` (`enhr.c`) + `intermediate_certificate[]` (`enhr.d`); empty → 6.
     PKIX validation against the two built-in roots (Eureka Root CA / Cast Root CA, `aibe.l`), revocation disabled;
     `CertPathValidatorException` → 8 ("client auth cert not trusted"); `ClassCastException` → 7.
  4. CRL: uses `crl` bytes from the response (`enhr.h`) if non-empty, else `aibe.b(ctx)`: a previously downloaded CRL
     bundle file (`aiax`) or an async download. `aibe.a(...)` verifies the CRL (`enit`/`eniw`) and checks the cert path:
     invalid → 12 (13 if empty), time-invalid → 14, revoked → 15 (16 if downloaded CRL). If the response CRL is invalid it
     retries with the backup CRL. Codes 1–4 are "success with CRL …" variants and still count as success (`aibe.i`).
  5. Signature: algorithm string from `aibe.d(enhr)`: `signature_algorithm` (`enhr.e`) 1 → "withRSA", 2 → "withRSAandMGF1";
     `hash_algorithm` (`enhr.g`) 0 → "SHA1", else "SHA256". `Signature.initVerify(leafPublicKey); update(senderNonce); update(peerCertDer); verify(enhr.b)`.
     Note `update(bArr)` uses the response's `sender_nonce` bytes (`bArrQ2`), then the TLS peer cert DER. Failure → 9.
  6. If `castDevice.j(1)` (capability bit 1 = video out), checks every cert for policy OID extension `2.5.29.32` containing
     the DER bytes `06 0A 2B 06 01 04 01 D6 79 02 05 02` (= OID 1.3.6.1.4.1.11129.2.5.2, "audio-only" policy); present →
     11 ("device capability not supported").
- Outcome `aibe.h(code)`: success (0–4) → `aiad.E(code == 1)` (finish connecting). Failure → optional "error message app"
  launch (`DeviceAuthConfigs__launch_error_message_app_when_authentication_failed`, default false, app id `0C26DAE9`), then
  `aiad.G(status, false, ...)` which calls listener/GetService `onConnectionFailed` with status: 1→2287, 2→2290, 3→2291,
  4→2292, 5→2277, 6→2278, 7→2279, 8→2280, 9→2281, 10→2282, 11→2283, 12→2284, 13→2288, 14→2293, 15→2285, 16→2289,
  17→2286, other→2255. The socket is then closed via the normal failure path (`G` sets state 0; `F` runs on socket close).
- There is **no** timeout-based skip: if the receiver never answers the challenge the connection stays in "connecting"
  until the socket fails (**not determined** whether an explicit auth timeout exists elsewhere).

### 5.4 Finish connecting `aiad.E(boolean)` [apk]
- Sends virtual-connection `CONNECT` (`aiau.c()`), then creates the heartbeat channel, sets state 2 (connected), and either
  rejoins `last_application_id/last_session_id` (`aa()`), or calls listener `onConnected(true)` (`J(true)`) and sends
  `GET_STATUS` (`aibo.b()`).

### 5.5 Virtual connection payload (`defpackage/aiau.java`) [apk]
Namespace `urn:x-cast:com.google.cast.tp.connection`, destination `receiver-0` (device) or the app `transportId`
(`aiad.z`: `sessionId` is used instead of `transportId` when `aizc.w()` is true):
```json
{"type":"CONNECT","origin":{"package":"<callingPackage>"},
 "userAgent":"Android CastSDK,<gmsVersionCode>,<Build.MODEL>,<Build.PRODUCT>,<Build.VERSION.RELEASE>",
 "senderInfo":{"sdkType":1,"version":"<gmsVersionCode>","platform":1,"systemVersion":"<RELEASE>",
               "model":"<MODEL>","connectionType":<1 if castDevice.r() (cloud/relay) else 2>},
 "protocolVersion":<3 if MessageChunking__is_enabled else 0>,
 "connType":<JoinOptions.a, only for the app connection>}
```
`CLOSE` = `{"type":"CLOSE"}` to the app transport id on explicit disconnect. On `CONNECTED` with `protocolVersion` the
negotiated version (0 or 3; 1 and 2 are treated as 0) is applied to the message builder.

### 5.6 Heartbeat (`defpackage/aibh.java`) [apk]
Namespace `urn:x-cast:com.google.cast.tp.heartbeat`, destination `transport-0`. A scheduled task runs every
`heartbeat_interval_ms` = **1000 ms** (`ftjv.k`); with the new mechanism (`CastControllerConfigs__use_new_heartbeat_mechanism`,
default true) it sends `{"type":"PING"}` once per `heartbeat_timeout_ms` = **10000 ms** cycle and, if no message arrives
before the cycle ends, disconnects with **2256**. Any received message counts as PONG; incoming `PING` is answered with
`{"type":"PONG"}`.

### 5.7 Receiver namespace requests (`defpackage/aibo.java`, `urn:x-cast:com.google.cast.receiver`, dest `receiver-0`) [apk]
- `GET_STATUS`: `{"requestId":n,"type":"GET_STATUS"}` (20 s timeout).
- `LAUNCH` (`aibo.a`): `{"requestId":n,"type":"LAUNCH","appId":id, "senderDeviceName":<Settings.Global device_name; only if
  ReceiverControlChannelFeatures__enable_sender_device_name_in_launch, default false>, "language":<LaunchOptions.b if non-null>,
  "supportedAppTypes":["WEB"] or ["WEB","ANDROID_TV"] (when LaunchOptions.c androidReceiverCompatible; `CastToNative__enabled` default true),
  "appParams":{"launchCheckerParams":{"credentialsData":{"credentials":..,"credentialsType":..}}} (when LaunchOptions.d set)}`.
  Timeout 65 s → failure 15.
- `STOP`: `{"requestId":n,"type":"STOP","sessionId":s}`.
- `SET_VOLUME`: see table codes 7/8. `SET_USER_EQ` for equalizer.
- Responses: `RECEIVER_STATUS` (parses `status.applications[0]`, `status.volume.{level,muted,stepInterval}`, `isActiveInput`,
  `isStandBy`, `userEq`), `LAUNCH_ERROR` (`reason`, `extendedError` → user-accept dialog codes 2019–2022), `LAUNCH_STATUS`
  (`USER_PENDING_AUTHORIZATION` shows a dialog), `INVALID_REQUEST` (`reason` → 2001 or 13).
- After a launch completes, `aiad.z()` connects to the app (CONNECT to transport id) and reports `onApplicationConnected`.

---

## 6. Discovery and MediaRouteProvider

### 6.1 mDNS (`defpackage/aids.java`, `defpackage/aidt.java`) [apk]
- Service type `_googlecast._tcp.local` (`btsc.a(...)`, "Cast mDNS Scanner"); subtypes `_<hash>` derived from the requested
  control categories (`aizt.h(criterion)`) are added to the MdnsSearchOptions and matched against `MdnsServiceInfo.e()`
  only when device version (`ve`) >= 4.
- TXT keys parsed in `aidt.a(MdnsServiceInfo, ...)` → `CastDevice` builder `ahsm` (field names from `ahsm`/`CastDevice`):
  - `id` → deviceId (required; missing → entry rejected). Address = IPv4 (`b()`), or IPv6 (`c()`) if IPv6 enabled.
  - `fn` → friendlyName (fallback: service instance name).
  - `md` → modelName; regex `(Eureka|Chromekey)( Dongle)?` replaced by `Chromecast`; missing → "Cast Device".
  - `ve` → deviceVersion (int as string; parse error → 0).
  - `st` → status: 0 → 0, else -1 (code: `i2 != 0 ? -1 : 0`, i.e. only "0" maps to 0; `1` branch is dead code).
  - `ca` → capabilities int (parse error → 0).
  - `rs` → stored as `aidt.c` (receiver status text, route description candidate), not in CastDevice.
  - `rm` → receiverMetricsId. `ic` → icon path, turned into a WebImage URL on the device address (`aimk.e`).
  - `nf` → rcnEnabledStatus (1,2,3 valid; else default from `ftmv.b()`).
  - `bs` → hotspotBssid. `cd` → cloudDeviceId (if `ftlo.c()`). `wp` → wakeupServicePort (if `aizc.g()`).
  - `ct` → `aidt.d` (if `aizc.d()`), `rr` → `aidt.f` — passed to the publish record (`aihs`), semantics **not determined**.
  - `ahsm.f` = SRV port; `ahsm.o` = lowest two IP bytes (`ainl.l`); `ahsm.k` = service instance name.
- Goodbye packets (`k()`) remove the entry and notify offline unless another entry refers to the same device (`CastDevice.s`).

### 6.2 Capability bitmask `ca` semantics used in code [apk]
`CastDevice.j(mask)` = all bits set. `defpackage/aily.java`: bit 64 → dynamic group (`toString` "[dynamic group]"),
bit 32 (without 64/128) → static multizone group, bit 128 → speaker pair (`g()`), bit 65536 → "f()" (gated by CastEurekaInfo.b),
bit 4 + !bit 1 → audio-only (`aixw.b`: deviceType 2 = audio, 1 = TV when bits 4 and 1, else 0), bit 2048 and 6144 (2048|4096)
checked for volume control (`aixw.a`, `aiad.r/s`), bit 1 → video-out (deviceauth policy check). Public names are not in the
decompiled code (**not determined** beyond usage).

### 6.3 Route publishing (`defpackage/aion.java` `m(aift)`) [apk]
- Route id = `castDevice.g()` (device id, `__cast_nearby__` prefix stripped); name = friendlyName (optionally prefixed with
  discovery markers `[C M T] - ` when `SETTINGS_KEY_CAST_ENABLE_DISCOVERY_MARKERS`).
- Builder calls (keys from `defpackage/iye.java`): `status` (description) = receiver status text or modelName for cloud
  devices; `canDisconnect=false`; `connecting` bool; `connectionState`; `deviceType` = `aixw.b()`; `volumeHandling` = 1 only
  if `!castDevice.j(6144)` when connected; `volume` = round(level * max); `volumeMax` = `media:max_volume` 20 or
  `media:max_volume_audio_out_only` 50 (audio-only or model "Chromecast Audio"); `playbackType=1` (remote);
  `controlFilters` from `aift.g`; `presentationDisplayId`; optional `deduplicationIds`.
- **Extras bundle** (`iyeVar.j(bundle)` → key `extras`): `castDevice.i(bundle)` ⇒
  `bundle.putParcelable("com.google.android.gms.cast.EXTRA_CAST_DEVICE", castDevice)`, plus
  `com.google.android.gms.cast.EXTRA_RUNNING_RECEIVER_APP_ID` (String) when known. Dynamic-session routes add
  `com.google.android.gms.cast.EXTRA_SESSION_ID` and `com.google.android.gms.cast.EXTRA_ENDPOINT_DEVICE_ID`.
- Control filters (`defpackage/aicn.java`): `a` = IntentFilter with category `com.google.android.gms.cast.CATEGORY_CAST`;
  `b` = list with REMOTE_PLAYBACK `PLAY` (http/https + 30 image/audio/video/HLS/DASH MIME types), one filter per action
  PAUSE/RESUME/STOP/SEEK/GET_STATUS/START_SESSION/GET_SESSION_STATUS/END_SESSION, and
  `com.google.android.gms.cast.CATEGORY_CAST_REMOTE_PLAYBACK` + `ACTION_SYNC_STATUS`. `aict` adds `aicn.a` always and `aicn.b`
  for media-capable devices.
- Control category parsing (`defpackage/aipp.java` `c()`): `com.google.android.gms.cast.CATEGORY_CAST[/<appId>[/<ns1,ns2…>[/<flags>]]]`
  (also `_GHA`, `_DYNAMIC_SESSION` variants); namespaces are `%`-hex-encoded (4 hex digits per char) and stored as
  `"%"+namespace` criteria; `REMOTE_PLAYBACK` maps to the generic player app id `CC1AD845` (`ftlx.e`). More than 5 segments → error.

---

## 7. Dynamite (`com.google.android.gms.cast.framework.dynamite`) [apk]

- The module name appears only in GMS-wide tables: `defpackage/anaa.java` lines 388–393 (module registry entry
  `amzz.CAST_FRAMEWORK_DYNAMITE`, name `cast.framework.dynamite`, product `PRODUCT_ID_CAST`) and `defpackage/amzp.java`
  (`"com.google.android.gms.cast.framework.dynamite" → fkto.DEVICE_CONNECTIVITY_SERVICE` / `amzu.DEFAULT_CAST_FRAMEWORK_DYNAMITE`).
- No `ICastDynamiteModule` class, no `com/google/android/gms/cast/framework/**` sources, and no
  `dynamite/descriptors/com/google/android/gms/cast*` ModuleDescriptor exist in this APK's decompiled tree
  (only `ads`, `cronet`, `googlecertificates`, `providerinstaller` descriptors are present). The jadx `resources/`
  directory is empty, so no asset/apk for the module could be inspected.
- Conclusion: the Cast framework dynamite module is **not contained in this APK** (it is a separately delivered Chimera
  module); its `MODULE_VERSION` and `ICastDynamiteModule` transaction codes are **not determined** from these sources.
  The only MODULE_VERSION constant in the tree is `com.google.android.gms.ads.dynamite` = 242335000
  (`com/google/android/gms/dynamite/descriptors/com/google/android/gms/ads/dynamite/ModuleDescriptor.java`), which
  `aiwf`/`aivn` merely log as the "APK version".

---

## 8. Open items (not determined)

1. The server-side Feature[] list returned by `ModuleManager.fetchFeatures` for the Cast module (module manifest, not Java).
2. `aibo.h(ahzi, boolean, DeviceStatus)` (which emits `onApplicationStatusChanged` / fills `DeviceStatus.d`) and
   `aiad.A()` (socket connect sequence) did not decompile; behaviour inferred only from callers.
3. `aiaq` (cxless controller) was not analysed line by line; it exposes the same abstract API as `aiad` (`ahzm`).
4. Where `ahym.k(String, byte[])` (expected TLS public-key hash `N`) gets its value — no caller found in `aiad`/`ahzy`.
5. Semantics of TXT keys `ct`, `rr`, `rs` beyond being forwarded to the publish record (`aihs`).
6. Cast remote-display / firstparty / RCN service ids and their stubs.
7. Dynamite module contents (section 7).
8. `ahsq.a()` names for 2017/2300/2301 are not present as switch cases; only numeric values are known.
