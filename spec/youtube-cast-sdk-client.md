# YouTube 19.17.42 – embedded Google Cast client SDK, as seen from the APK

Source: jadx decompilation of YouTube 19.17.42 (Android 15 Google Play emulator image).
Paths below are relative to the jadx `sources` root. Obfuscated names (e.g. `defpackage/onh.java`)
are the names in this specific build. Every fact is tagged `[apk]`; anything not visible in the
decompiled code is marked "not determined".

Conventions for AIDL evidence (all in `defpackage/fup.java`, `defpackage/fuq.java`) [apk]:

- Proxy base `fup`: `nw()` = obtain Parcel + `writeInterfaceToken(descriptor)`;
  `nx(code, p)` = `transact(code, p, reply, 0)` + `readException()` and returns reply;
  `ny(code, p)` = `transact(code, p, reply, 0)` + `readException()` (void);
  `sa(code, p)` = `transact(code, p, null, FLAG_ONEWAY=1)` → **oneway**.
- Stub base `fuq`: `onTransact` → `enforceInterface(descriptor)` then `dispatchTransaction(code, ...)`;
  `enforceNoDataAvail` throws if unread data remains.
- `fur.a(parcel, CREATOR)` reads a nullable Parcelable (int flag then object);
  `fur.f(parcel, parcelable)` writes a nullable Parcelable (int 0 / int 1 + writeToParcel);
  `fur.h(parcel, iinterface)` = `writeStrongBinder`; `fur.i(parcel)` = readInt != 0 (boolean).

---

## 1. SDK identification

| Item | Value | Evidence |
|---|---|---|
| cast-framework / play-services-cast library version string | `"21.5.0"` | `defpackage/ojy.java` (`b = "21.5.0"`, SessionFlowSummary), `defpackage/ojs.java` (FeatureUsageAnalytics `a = "21.5.0"`), `defpackage/ojr.java` (ApplicationAnalyticsUtils), `defpackage/ons.java:188` (sdk version written into analytics proto) [apk] |
| Google Play services client-library version code (`GOOGLE_PLAY_SERVICES_VERSION_CODE`) | `241802000` | `defpackage/opu.java` static init `c = 241802000` [apk]. Same constant is returned by every client-side stub "getSupportedVersion" method (e.g. `defpackage/okj.java` code 10, `defpackage/ogn.java` ICastConnectionController code 5 / ISessionProvider code 4 / ISessionProxy code 6, `defpackage/oin.java` code 4) [apk] |
| Dynamite module id | `"com.google.android.gms.cast.framework.dynamite"` | `defpackage/okg.java` `okg.a(Context)` [apk] |
| Impl class requested from module | `"com.google.android.gms.cast.framework.internal.CastDynamiteModuleImpl"`; binder is `queryLocalInterface("com.google.android.gms.cast.framework.internal.ICastDynamiteModule")` | `defpackage/okg.java` [apk] |
| Version policy | `oxk.a` = `new oxe(1)` → `defpackage/oxe.java` branch `i == 1`: remote version via `oxh.b(context, id, true)` first; if remote version != 0 → load remote (`c = 1`); else fallback to local descriptor (`a(context,id)`) → local (`c = -1`). No explicit minimum version is requested; only "remote version != 0" | `defpackage/okg.java`, `defpackage/oxe.java`, `defpackage/oxk.java:244-330` [apk] |
| Remote version lookup | content provider `content://com.google.android.gms.chimera/api/<moduleId>?requestStartUptime=…` (or `api_force_staging`) | `defpackage/oxk.java:451` [apk] |
| Local module descriptor for cast | none: `com/google/android/gms/dynamite/descriptors/` only contains `cronet/dynamite` (MODULE_VERSION=1) and `measurement/dynamite` (MODULE_VERSION=111) | directory listing [apk] |
| Loader binder calls | `IDynamiteLoaderV2` codes 3 (`loadModule2NoCrashUtils`-style: ctx, moduleId, version int, cursor) or 2 (fallback) | `defpackage/oxk.java:289-330` [apk] |
| Minimum GMS apk version per client (`getMinApkVersion`) | `onh` (legacy Cast client) `12800000`; `oni` (CXLESS client) `19390000`; `ond` (CastApi/service 161) `12451000` | `defpackage/onh.java a()`, `defpackage/oni.java a()`, `defpackage/ond.java a()` [apk] |
| Version gates inside the dynamite-served interfaces | `ISession.getSupportedVersion() >= 211100000` before calling `ISession` code 18 (`defpackage/ojg.java n()`); `IMediaRouterCallback.getSupportedVersion() >= 220400000` before using code 8 (`defpackage/okn.java o()`) [apk] | |

Other version constants seen: `otx.f()` enables "dynamic lookup" (chimera content-provider lookup for the bind
target) only if `a() >= 211700000`, which is false for all three cast clients, so binding is by plain
intent action + package (`defpackage/otx.java:325-327`, `defpackage/akne.java` ctor `(String, boolean)`) [apk].

---

## 2. Service binding (GmsClient / IGmsServiceBroker)

### 2.1 Clients present in the APK

| Client class | Service id (`GetServiceRequest.serviceId`) | Start-service action (`d()`) | Interface descriptor checked (`c()`) | Used by |
|---|---|---|---|---|
| `defpackage/oni.java` (`"CastClientImplCxless"`) | **10** (`super(context, looper, 10, …)`) | `com.google.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE` | `com.google.android.gms.cast.internal.ICastDeviceController` | `defpackage/ohr.java` → API `"Cast.API_CXLESS"` in `defpackage/oht.java` (the CastClient used by the framework `CastSession`, `defpackage/oil.java` via `defpackage/ohj.java a()`) [apk] |
| `defpackage/onh.java` (`"CastClientImpl"`) | **10** | same | same | `defpackage/ohg.java` → API `"Cast.API"` created in `defpackage/ohj.java` static init but the `nyp` object is discarded (not assigned). No other `new onh(` call site exists; effectively unused in this APK [apk] |
| `defpackage/ond.java` | **161** | `com.google.android.gms.cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE` (same action!) | `com.google.android.gms.cast.internal.ICastService` | `defpackage/omy.java` → API `"CastApi.API"` in `defpackage/onc.java` [apk] |

No `BIND_CAST_SERVICE` or other cast action string exists in the APK (grep over sources) [apk].

### 2.2 Bind mechanics (common GmsClient base `defpackage/otx.java`)

- Bind target: `akne(d(), f())` → package `"com.google.android.gms"`, flags `4225`, dynamic-lookup false
  (`defpackage/akne.java:58-62`, `defpackage/ouh.java`, `defpackage/ouj.java:68-70`:
  `new Intent(action).setPackage("com.google.android.gms")`, `bindService(..., 4225, ...)`) [apk].
- On `onServiceConnected` the binder is wrapped as `IGmsServiceBroker` proxy (`defpackage/ott.java`) [apk].
- `getService`: `otx.B()` builds `GetServiceRequest` and does
  `transact(46, parcel)` on the broker with interface token
  `"com.google.android.gms.common.internal.IGmsServiceBroker"`, parcel = `writeStrongBinder(IGmsCallbacks stub)`,
  `writeInt(1)`, then the SafeParcel of GetServiceRequest (`defpackage/otx.java:185-196`) [apk].
- `GetServiceRequest` fields (`com/google/android/gms/common/internal/GetServiceRequest.java`,
  SafeParcel field ids from `defpackage/oua.java` case 3) [apk]:
  - 1 `versionCode` = 6; 2 `serviceId` = 10 or 161; 3 `clientVersion` = `opu.c` = 241802000;
  - 4 `callingPackage` = `context.getPackageName()` (i.e. `com.google.android.youtube`);
  - 5 `accountAccessor` binder (only if `k()` – not for cast); 6 scopes (empty); 7 `extras` Bundle = `j()` (see 2.3);
  - 8 `account` null for cast (`oug.D()` returns `oty.a`; `k()` false); 10 `clientRequiredFeatures` = `N()` = empty array (`defpackage/oug.java N()`);
  - 11 `clientApiFeatures` = `h()`: for `oni` and `ond` = `ohm.n` (all 13 features, see 2.4); for `onh` = default empty (`otx.h()`);
  - 12 boolean = true (constructor arg); 13 int = 0; 14 boolean = `g()` → true for `oni` and `ond` (`g()` returns true), false for `onh`;
  - 15 `attributionTag` string (`this.A` or AttributionSource tag on API 31+).
- Callback: `IGmsCallbacks` stub `defpackage/ouq.java`: code 1 `onPostInitComplete(int status, IBinder, Bundle)`,
  code 3 `onPostInitCompleteWithConnectionInfo(int status, IBinder, ConnectionInfo)`; code 2 deprecated/ignored [apk].
- Post-init handling `defpackage/otn.java d()`: status must be **0**; else `ConnectionResult(status, pendingIntent from bundle "pendingIntent")`.
  On status 0, `otv.c()` checks `binder.getInterfaceDescriptor()` equals `c()` (the descriptor above) — mismatch → failure with `ConnectionResult(8)` [apk].
- `onh.n()` additionally accepts status **2300** (treated as 0 and sets bundle extra
  `"com.google.android.gms.cast.EXTRA_APP_NO_LONGER_RUNNING"=true` in the connection hint) (`defpackage/onh.java:150-170`) [apk].
  `oni` has no such override → only status 0 is a success for the CXLESS client [apk].
- No client-side connection timeout is implemented in `otx`, `oht`, or `oil` (grep for timeout/sendMessageDelayed returns nothing) → "not determined / none seen" [apk].

### 2.3 Extras Bundle (`j()`) sent in GetServiceRequest

`oni.j()` (`defpackage/oni.java:60-72`) [apk]:

| Key | Type | Value |
|---|---|---|
| `com.google.android.gms.cast.EXTRA_CAST_DEVICE` | Parcelable `CastDevice` | `castDevice.e(bundle)` (`com/google/android/gms/cast/CastDevice.java e()`) |
| `com.google.android.gms.cast.EXTRA_CAST_FLAGS` | long | `0L` |
| `connectionless_client_record_id` | String | `UUID.randomUUID().toString()` per `ohh` instance (`defpackage/ohh.java d`) |
| (merged) caller bundle `ohh.b` | | from `oil.r()` (`defpackage/oil.java:106-116`): `com.google.android.gms.cast.EXTRA_CAST_FRAMEWORK_NOTIFICATION_ENABLED` (boolean, `notificationOptions != null`), `com.google.android.gms.cast.EXTRA_CAST_REMOTE_CONTROL_NOTIFICATION_ENABLED` (boolean), `com.google.android.gms.cast.EXTRA_CAST_ALWAYS_FOLLOW_SESSION_ENABLED` (boolean, `okq.f`) |

`onh.j()` (legacy, unused) additionally puts `"listener"` = `BinderWrapper(ICastDeviceControllerListener stub)`,
`"last_application_id"` and `"last_session_id"` strings (`defpackage/onh.java:95-115`) [apk]. The CXLESS client does
**not** put a listener in the bundle; it registers it with controller transaction 18 (section 3).

`ond.j()` is not overridden → empty Bundle (`defpackage/ond.java`) [apk].

Keys `EXTRA_USE_ROUTE_CONNECTION` / `ROUTE_CONNECTION` do not occur anywhere in the APK (grep) [apk].

### 2.4 Requested API features (`ohm.n`) – all `Feature(name, version)` [apk] `defpackage/ohm.java`

| # | Name | version (long) |
|---|---|---|
| a | `client_side_logging` | 1 |
| b | `cxless_client_minimal` | 1 |
| c | `cxless_caf_control` | 1 |
| d | `module_flag_control` | 1 |
| e | `discovery_hint_supply` | 1 |
| f | `relay_casting_set_active_account` | 1 |
| g | `analytics_proto_enum_translation` | 1 |
| h | `integer_to_integer_map` | 1 |
| i | `relay_casting_set_remote_casting_mode` | 1 |
| j | `get_relay_access_token` | 1 |
| k | `get_cast_settings` | 1 |
| l | `set_bundle_setting` | 1 |
| m | `get_client_updated_info` | 1 |

Features required per individual call (checked against the server-advertised features from `ConnectionInfo`):
`cxless_client_minimal` (`ohm.b`) for the listener registration in `oht.d()` [apk];
`module_flag_control` (`ohm.d`) for `onc.a(String[])` (`defpackage/onc.java`);
`analytics_proto_enum_translation` (`ohm.g`) for method 8426 and `integer_to_integer_map` (`ohm.h`) for method 8427 (`defpackage/oie.java`) [apk].

---

## 3. `ICastDeviceController` proxy (`defpackage/onn.java` + inline call sites)

Descriptor `com.google.android.gms.cast.internal.ICastDeviceController`. Proxy class `onn` only declares
`a()` (code 1) and `b(String)` (code 12); every other call is inlined at the call site using `onn.nw()`/`onn.sa()`.
**All calls use `sa()` → oneway (FLAG_ONEWAY).** No `nx`/`ny` on this interface anywhere [apk].

| Code | Semantics (as used by client) | Parameters written (in order) | Oneway | Call site (method id) |
|---|---|---|---|---|
| 1 | disconnect | none | yes | `onn.a()`; `oht.e()` via `ohp(0)` (8403); `oni.m()` on client disconnect [apk] |
| 4 | leave/stop current application (no args); client then waits for listener code 7/8/9 to complete pending result `t` | none | yes | `ogp` case 6 (`defpackage/ogp.java:84-89`), used from `defpackage/omr.java:55` (8408, relay-casting "RemoteConnectionManager" path) [apk] |
| 5 | stopApplication(sessionId) ; completes via listener 7/8/9 (`oht.s`) | `writeString(sessionId)` | yes | `defpackage/pci.java` case 1 (8409), triggered by `ICastConnectionController` code 3 [apk] |
| 7 | setVolume | `writeDouble(newLevel)`, `writeDouble(currentLevel = oht.i)`, `writeInt(muted = oht.j ? 1:0)` | yes | `defpackage/acrd.java:95-111` (8411) [apk] |
| 9 | sendMessage | `writeString(namespace)`, `writeString(message)`, `writeLong(requestId)` (`oht.e.incrementAndGet()`); result delivered by listener codes 10/11 keyed by requestId | yes | `defpackage/ohn.java` case 3 (8405) from `oht.b(ns, msg)`; message size limit 524288 chars [apk] |
| 11 | registerNamespace / setMessageReceivedCallbacks (add) | `writeString(namespace)` | yes | `defpackage/ohn.java` case 4 (8413): always sends code 12 first, then 11 if callback != null [apk] |
| 12 | unregisterNamespace / removeMessageReceivedCallbacks | `writeString(namespace)` | yes | `onn.b(String)`; `ohn` case 2 (8414) and case 4 [apk] |
| 13 | launchApplication | `writeString(applicationId)`, `fur.f(LaunchOptions)` ; completes via listener code 2 (success) / 3 (failure) → `oht.s` | yes | `defpackage/ohn.java` case 0 (8406), triggered by `ICastConnectionController` code 2 [apk] |
| 14 | joinApplication | `writeString(applicationId)`, `writeString(sessionId)`, `fur.f(JoinOptions)` (null when coming from `ICastConnectionController` code 1) | yes | `defpackage/oht.java a()` (8407) [apk] |
| 17 | (no args) sent immediately after 18; the client then expects listener code 14 (connect result). Name not determined (behaves like "connect"/"requestStatus") | none | yes | `defpackage/ogp.java` case 5 (registration half of 8428) [apk] |
| 18 | registerListener (ICastDeviceControllerListener) | `fur.h(listenerStub)` (`oht.b`, class `ohs`) | yes | `defpackage/ogp.java` case 5 [apk] |
| 19 | unregister half of the 8428 registration; no params; name not determined | none | yes | `defpackage/ohp.java` case 2 [apk] |

Codes 2, 3, 6, 8, 10, 15, 16 are not used anywhere in the APK → semantics not determined [apk].

Method-id constants (GoogleApi "methodKey") seen: 8403 disconnect, 8405 sendMessage, 8406 launch, 8407 join,
8408 leave(code 4), 8409 stop, 8411 setVolume, 8413 setMessageReceivedCallbacks, 8414 removeMessageReceivedCallbacks,
8415 unregisterListener, 8428 registerListener (`defpackage/oht.java`, `defpackage/ogn.java`, `defpackage/acrd.java`) [apk].

---

## 4. `ICastDeviceControllerListener` stub (`defpackage/ono.java`)

Descriptor `com.google.android.gms.cast.internal.ICastDeviceControllerListener`. The stub never writes a
reply (`parcel2.writeNoException()` is absent for every case) → the interface is treated as **oneway** on the
client side; the server must transact with FLAG_ONEWAY or not expect a reply [apk].
Two implementations: `defpackage/ohs.java` (for `oht`/CXLESS – the live one) and `defpackage/ong.java` (legacy `onh`).

| Code | Params read (order) | `ohs` handler → effect (CXLESS path) |
|---|---|---|
| 1 | `readInt(reason)` | `i(int)` → posts `o(…,12)`: resets volume/metadata/state, `oht.r = 1` (disconnected), calls `nji.A(reason)` (= onDisconnected → `oik.A` → `ody.n`), clears namespace callbacks, unregisters listener (8415) (`o.java:152-177`) [apk] |
| 2 | `fur.a(ApplicationMetadata)`, `readString(applicationStatus)`, `readString(sessionId)`, `fur.i(wasLaunched)` | `a(...)` → completes pending launch/join result `oht.s` with `onf(Status(0), metadata, status, sessionId, wasLaunched)`; stores `g`,`h` [apk] |
| 3 | `readInt(status)` | `b(int)` → `oht.l(status)`: fails pending launch/join `s` with `Status(status)` [apk] |
| 4 | `readString`, `readDouble`, `fur.i` | `n()` → no-op (legacy status update) [apk] |
| 5 | `readString(namespace)`, `readString(message)` | `k(ns,msg)` → posts `ndi(…,5)`: looks up `ohi` callback registered for namespace in `oht.p` and calls `ohi.a(message)` [apk] |
| 6 | `readString(namespace)`, `createByteArray()` | `o(byte[])` → no-op (binary messages dropped) [apk] |
| 7 | `readInt(status)` | `d(int)` → `oht.n(status)`: completes pending stop/leave result `t` (0 → `Status(0)`, else failure) [apk] |
| 8 | `readInt(status)` | `f(int)` → `oht.n(status)` (same as 7) [apk] |
| 9 | `readInt(reason)` | `c(int)` → `oht.n(reason)` + posts `o(…,14)` → `nji.C(reason)` (onApplicationDisconnected → `oij.C` → `oil.d(reason)` + `ojg.p(reason)`, i.e. ISession code 13) [apk] |
| 10 | `readString(namespace)`, `readLong(requestId)`, `readInt(status)` | `m(requestId,status)` → `oht.m`: completes sendMessage task for requestId (0 success, else `Status(status)`) [apk] |
| 11 | `readString(namespace)`, `readLong(requestId)` | `l(requestId)` → `oht.m(requestId, 0)` (success) [apk] |
| 12 | `fur.a(ApplicationStatus)` (single string field id 2) | `e(...)` → posts `b(…,12)`: updates `oht.h` and calls `nji.E()` (onApplicationStatusChanged) if changed or first [apk] |
| 13 | `fur.a(DeviceStatus)` (fields: 2 double volume, 3 bool mute, 4 int activeInputState, 5 ApplicationMetadata, 6 int standbyState, 7 EqualizerSettings, 8 double stepInterval) | `h(...)` → posts `b(…,11)`: updates metadata (`nji.D`), volume/mute (`nji.G`), active input / standby (`nji.B`/`nji.F`), equalizer [apk] |
| 14 | `readInt(status)` | `g(int)` → posts `o(…,13)`: if 0 → `oht.r = 3` (connected), `c = d = true`, `nji.x()` (onConnected → `oik.x` → ISession code 1 via `oiq.k()`); else `r = 1` and `nji.y(status)` (onConnectionFailed) [apk] |
| 15 | `readInt(reason)` | `j(int)` → posts `o(…,15)`: `oht.r = 4`, `nji.z(reason)` (onConnectionSuspended → `oik.z` → `oiq.h(reason)` ICastSession code 2) [apk] |

---

## 5. `ICastService` (service id 161, `"CastApi.API"`) – `defpackage/onq.java` + `defpackage/ogp.java`

Descriptor `com.google.android.gms.cast.internal.ICastService`. Proxy `onq` declares no methods; calls are inlined.
All calls are `sa()` → **oneway** [apk].

| Code | Params | Callback | Call site / purpose |
|---|---|---|---|
| 5 | `fur.h(IBundleCallback stub)`, `writeStringArray(flagNames)` | `omz` → task result Bundle | `onc.a(String[])` (8425, requires feature `module_flag_control`) – "get flags". Used with `com.google.android.gms.cast.FLAG_CLIENT_SESSION_ANALYTICS_ENABLED`, `…FLAG_CLIENT_SESSION_ANALYTICS_MODE`, `…FLAG_FIRELOG_UPLOAD_MODE`, `…FLAG_ANALYTICS_LOGGING_BUCKET_SIZE`, `…FLAG_CLIENT_FEATURE_USAGE_ANALYTICS_ENABLED`, `…FLAG_CLIENT_ANALYTICS_ENABLED`, `…FLAG_ANALYTICS_CONSENT_TIMEOUT_SECONDS` (`defpackage/oie.java:159`) and `com.google.android.gms.cast.FLAG_OUTPUT_SWITCHER_ENABLED` (`defpackage/okq.java`) [apk] |
| 6 | `fur.h(IBundleCallback stub)`, `writeStringArray(names)` | `ona` → Bundle | `ogp` case 7 (8426, feature `analytics_proto_enum_translation`): names `com.google.android.gms.cast.DICTIONARY_CAST_STATUS_CODES_TO_APP_SESSION_ERROR`, `…DICTIONARY_CAST_STATUS_CODES_TO_APP_SESSION_CHANGE_REASON` (`defpackage/oie.java:191`) [apk] |
| 7 | `fur.h(IBundleCallback stub)`, `writeStringArray(names)` | `onb` → Bundle | `ogp` case 9 (8427, feature `integer_to_integer_map`): `com.google.android.gms.cast.MAP_CAST_STATUS_CODES_TO_CAST_REASON_CODES` (`defpackage/oie.java:282`); result consumed by `oie.a(int)` as Integer→Integer map `obs.a` [apk] |

Bundle value types the client reads back: `FLAG_CLIENT_SESSION_ANALYTICS_MODE` int; `FLAG_CLIENT_SESSION_ANALYTICS_ENABLED`,
`FLAG_CLIENT_FEATURE_USAGE_ANALYTICS_ENABLED`, `FLAG_CLIENT_ANALYTICS_ENABLED` boolean; `FLAG_ANALYTICS_CONSENT_TIMEOUT_SECONDS`,
`FLAG_FIRELOG_UPLOAD_MODE`, `FLAG_ANALYTICS_LOGGING_BUCKET_SIZE` long (`defpackage/oie.java:167-185`) [apk].
The getters use `othVarB.b = false` (auto-resolve-missing-features off) so a server lacking the feature makes the task fail without crashing [apk].

`IBundleCallback` stub `defpackage/onl.java`: descriptor `com.google.android.gms.cast.internal.IBundleCallback`,
code 1: `fur.a(Bundle)` → `a(Bundle)`; no reply written (oneway-style) [apk]. No `IStatusCallback` for cast is present [apk].
Codes 1-4 and >7 of ICastService are not used → not determined.

---

## 6. Connection handshake order (CXLESS client, `defpackage/oht.java` + `defpackage/oil.java`)

Trigger: the cast-framework dynamite module (server side, in GMS) calls `ISessionProxy` code 2 (`start(Bundle)`) or 3
(`resume(Bundle)`) on YouTube's `ogn` stub (`defpackage/ogn.java` case 8) → `oil.i/h(bundle)` → `oil.r(bundle)` [apk].

1. `oil.r()` extracts `CastDevice` from the route bundle (`CastDevice.b(bundle)`, key
   `com.google.android.gms.cast.EXTRA_CAST_DEVICE`). If null: ISession code 9 (`j()`) and then code 15 (`k()`, writes int 2153)
   or code 12 (`l()`, writes int 2151) and returns [apk].
2. Builds `ohh` (device, callback `oij`, extras bundle with the three EXTRA_CAST_* booleans), `ohj.a()` → `new oht(...)`,
   adds `oik` listener (`h()`), then `oht.d()` [apk].
3. `oht.d()` (`defpackage/oht.java:117-130`): `r = 2` (connecting); `D(registerListener)` with key
   `"castDeviceControllerListenerKey"`, feature `cxless_client_minimal`, method id 8428. The GoogleApi machinery
   first binds + `getService` (section 2), then runs `ogp(5)`: **controller code 18 (registerListener)**, then **code 17** [apk].
4. The client waits for **listener code 14** with status 0 → `r = 3`, `nji.x()` → `oik.x()` → `oiq.k()` = **ICastSession code 1**
   (`fur.f(null)` + `ny(1)`) telling the framework the connection is up; also `olv.l()` (RemoteMediaClient re-register) [apk].
   Non-zero status → `nji.y(status)` (connection failed) [apk].
5. The framework then calls **ICastConnectionController** (YouTube stub `ogn` case 6, descriptor
   `com.google.android.gms.cast.framework.ICastConnectionController`):
   - code 1 `joinApplication(String appId, String sessionId)` → `oht.a(appId, sessionId, null)` → controller code 14;
   - code 2 `launchApplication(String appId, LaunchOptions)` → `ohn(…,0)` → controller code 13 (8406);
   - code 3 `stopApplication(String sessionId)` → controller code 5 (8409);
   - code 4 `disconnect(int reason)` → `oil.d(reason)`;
   - code 5 `getSupportedVersion()` → 241802000 [apk].
   Each stub call only proceeds if `oht.c()` (`r == 3`) else is silently dropped; reply is `writeNoException()` [apk].
6. Launch/join completion: listener code 2 → `onf` result → `oil.m(task)` → `oiq.a(metadata, status, sessionId, wasLaunched)`
   = **ICastSession code 4**; failure (listener 3 or exception) → `oiq.b(statusCode)` = **ICastSession code 5**
   (`2476` for non-API exceptions). Status accepted: `onf.a.c()` i.e. `Status.isSuccess()` (code 0) [apk].
7. Disconnect: `oil.d()`/`oil.e(z)` → `oht.e()` → controller code 1 (8403), clears namespaces, unregister (8415 → code 19);
   `oiq.j(stopCasting)` = **ICastSession code 6** (`writeInt(bool)`, `writeInt(0)`) then `ojg.p(0)` = ISession code 13 [apk].
8. Timeout: none implemented client-side (not determined / absent) [apk]. On `RemoteException` during registration the
   task fails with the exception (`defpackage/ohn.java:103-106`) [apk].

`oht.r` states: 1 disconnected, 2 connecting, 3 connected, 4 suspended (`defpackage/oht.java`, `o.java`) [apk].
Pending-result guards: a second launch/join while one is pending fails the previous with status `2477`
(`oht.r(ppr)`); a second stop while pending fails with `2001` (`oht.s(ppr)`) [apk].

---

## 7. MediaRouter side

- YouTube uses **androidx MediaRouter directly** (obfuscated `dfw` = `MediaRouter`, `dfq` = `MediaRouteSelector`
  with Bundle key `"controlCategories"`, `dfu` = `RouteInfo`, `bmi` = `MediaRouter.Callback`; package dir `androidx/mediarouter`
  exists) – `defpackage/dfq.java:35,64`, `defpackage/dfw.java:69`, `defpackage/acmp.java c()` (`dfw.b(context)` = `getInstance`) [apk].
- The cast-framework `IMediaRouter` is implemented **client-side** by YouTube (`defpackage/okq.java` extends stub `okj`,
  descriptor `com.google.android.gms.cast.framework.internal.IMediaRouter`) and handed to the dynamite module in
  `ICastDynamiteModule.newCastContextImpl` (code 1). So the GMS-side framework drives androidx MediaRouter through this stub [apk]:

  | IMediaRouter code (stub `okj`) | Params | Impl (`okq`) |
  |---|---|---|
  | 1 | Bundle selector, IMediaRouterCallback | `d()`: `dfq.a(bundle)`, store `okn(callback)` |
  | 2 | Bundle selector, int flags | `c()`: `MediaRouter.addCallback(selector, cb, flags)` |
  | 3 | Bundle selector | `f()`: removeCallback |
  | 4 | Bundle selector, int flags | `l()`: `MediaRouter.isRouteAvailable(selector, flags)` → bool |
  | 5 | String routeId | `h()`: `selectRoute(route)` |
  | 6 | – | `g()`: select default route |
  | 7 | – | `k()`: selected == default → bool |
  | 8 | String routeId | `a()`: returns route `extras` Bundle |
  | 9 | – | `b()`: selected route id |
  | 10 | – | returns 241802000 |
  | 11 | – | `e()`: remove all callbacks |
  | 12 | – | `j()`: bluetooth route is selected → bool |
  | 13 | int | `i()`: `MediaRouter.unselect(reason)` |

  `IMediaRouterCallback` proxy `defpackage/okl.java` (descriptor `…internal.IMediaRouterCallback`, all `ny`, two-way):
  1 onRouteAdded(id, extras), 2 onRouteChanged, 3 onRouteRemoved, 4 onRouteSelected(id, extras) (legacy),
  6 onRouteUnselected(id, extras, reason), 7 getSupportedVersion() → int, 8 onRouteSelected(selectedId, routeId, extras)
  (used when version >= 220400000; group routes `-groupRoute` mapped to member route) (`defpackage/okn.java`) [apk].

- Control category format (`defpackage/ody.java r()`): `"com.google.android.gms.cast.CATEGORY_CAST" + "/" + APPID_UPPERCASE_HEX`
  then, if namespaces given, `"/" + ns1,ns2,…` (non-matching chars percent-encoded `%%%04x`), else a trailing `"/"`,
  and always suffixed `"//ALLOW_IPV6"`. `ody.q(appId)` = `r("…CATEGORY_CAST", appId, null)` →
  **`com.google.android.gms.cast.CATEGORY_CAST/233637DE///ALLOW_IPV6`** for the YouTube app id [apk].
- Selectors built:
  - cast-framework session provider `defpackage/qkj.java:62-75`: `ody.q(castOptions.d)` (no namespaces in CastOptions → `b()` empty) [apk];
  - framework discovery `defpackage/oko.java:48`, relay `defpackage/omw.java a()`: same `ody.q(appId)` [apk];
  - YouTube MDX selector `defpackage/acmp.java a(appId, cat2)` (`defpackage/fzc.java:4487`): categories
    `"MDX_MEDIA_ROUTE_CONTROL_CATEGORY_" + theme` (theme = `acet.b` = `"YouTube"`, `defpackage/fvk.java`), `android.media.intent.category.LIVE_AUDIO`,
    and `ody.q(castAppId)` [apk].
- Route extras read: `CastDevice.b(route.extras)` → key `com.google.android.gms.cast.EXTRA_CAST_DEVICE` (Parcelable CastDevice)
  (`defpackage/okn.java`, `defpackage/acmt.java:109`, `defpackage/aciq.java:401`, `defpackage/zte.java:139`) and
  `com.google.android.gms.cast.EXTRA_RUNNING_RECEIVER_APP_ID` (String) (`defpackage/omv.java:40`, `defpackage/omw.java:77`) [apk].
  Routes are also classified by `IntentFilter.hasCategory(ody.q(appId))` (`defpackage/aciu.java:114`, `defpackage/acja.java:91`) [apk].
- CastDevice SafeParcel layout (`com/google/android/gms/cast/CastDevice.java writeToParcel`): 2 deviceId, 3 hostAddress,
  4 friendlyName, 5 modelName, 6 deviceVersion, 7 servicePort, 8 icons list, 9 capabilities int, 10 status int,
  11 serviceInstanceName, 12 receiverMetricsId, 13 rcnEnabledStatus, 14 hotspotBssid, 15 ipLowestTwoBytes (byte[]),
  16 cloudDeviceId, 17 isCloudOnlyDevice (bool), 18 CastEurekaInfo (2 int, 3 bool, 4 bool), 19 Integer [apk].
  `d()` strips `"__cast_nearby__"` prefix from deviceId; capability bits checked: 2048, 4, 1, 32, 64 (`p()`, `c()`) [apk].

---

## 8. cast-framework usage (CastContext / SessionManager via dynamite)

YouTube uses the **framework path** (`CastContext` → `SessionManager` → `CastSession`), not the raw Cast API directly:
`defpackage/aceo.java:145` `oie.f(context, executor)` (CastContext.getSharedInstance async), `aceo.g()` registers a
`SessionManagerListener` (`ojh.c(acen, oil.class)`) [apk]. YouTube reaches the low-level `oht` only through
`CastSession.c` (`oil.c`) for `setMessageReceivedCallbacks` (`defpackage/acen.java k()`) and `sendMessage`
(`oil.l()` → `oht.b()`, `defpackage/alyt.java p()`), and `setVolume` (`defpackage/acrd.java Y()`) [apk].

OptionsProvider: manifest meta-data key `com.google.android.gms.cast.framework.OPTIONS_PROVIDER_CLASS_NAME`
(`defpackage/oie.java h()`), class `com/google/android/libraries/youtube/mdx/castclient/CastOptionsProvider.java` [apk].

`CastOptions` built by YouTube (`CastOptionsProvider.getCastOptions`, SafeParcel ids from `CastOptions.writeToParcel`) [apk]:

| field id | field | YouTube value |
|---|---|---|
| 2 | receiverApplicationId `d` | `castAppId` injected from `fyu.wh()`: `acet.j` (`afjr`, SparseArray keyed by pref `MdxReceiverAppVersion`) with default `afjr.a = "233637DE"` (`defpackage/afjr.java:296-299`, `defpackage/fyu.java:5210-5220`) [apk] |
| 3 | supportedNamespaces | empty list |
| 4 | stopReceiverApplicationWhenEndingSession `e` | `false` |
| 5 | LaunchOptions `f` | `relaunchIfRunning = !(mdxConfig.aa() || mdxModuleConfig.f == 1)` (`acet.f` = multiUserSession = 1 → false); `language` = default-locale tag; `androidReceiverCompatible = mdxConfig.av()`; credentialsData null |
| 6 | resumeSavedSession `g` | `!mdxConfig.ak()` |
| 7 | CastMediaOptions `h` | `afxt` builder default (media session enabled per builder; `CastOptions.c` fallback) |
| 8 | enableReconnectionService `i` | `!mdxConfig.ak()` |
| 9 | volumeDeltaBeforeIceCreamSandwich `j` | `0.05` |
| 10,11 | `k`,`l` | `false`,`false` |
| 12 | `m` (output switcher / media transfer) | `mdxMediaTransferReceiverEnabler.b()` |
| 13 | routeDiscoveryReceiverApplicationIds `a()` | empty list |
| 14 | `n` (remote-to-local) | `mdxMediaTransferReceiverEnabler.b()` |
| 15 | int | always 0 |
| 16 | `o` | `false` |
| 17 | CastExperimentOptions `p` | `new CastExperimentOptions(mdxConfig.af())` (one bool, field 2) |
| 18 | CastFeatureVersions `q` | `CastOptions.b` = `CastFeatureVersions(0)`, overwritten to `CastFeatureVersions(1)` in `oie` ctor (`castOptions.q = ody.l(1)`) before `newCastContextImpl` |

`ICastDynamiteModule` proxy `defpackage/okh.java` (descriptor `…framework.internal.ICastDynamiteModule`, two-way `nx`):

| Code | Method | Params |
|---|---|---|
| 1 | newCastContextImpl → `ICastContext` | IObjectWrapper(appContext), CastOptions (SafeParcel), IMediaRouter stub (`okq`), `writeMap(category → ISessionProvider binder)` |
| 2 | newSessionImpl → `ISession` | String category, String sessionId, ISessionProxy stub (`ogn(ojg,8)`) |
| 3 | newCastSessionImpl → `ICastSession` | CastOptions, IObjectWrapper(session), ICastConnectionController stub (`ogn(oil,6)`) |
| 5 | newReconnectionServiceImpl → `IReconnectionService` | IObjectWrapper(service), IObjectWrapper(sessionManager wrapped), IObjectWrapper(discoveryManager wrapped) |
| 6 / 7 | newFetchBitmapTaskImpl | wrappers + ints (w,h,0, long 2097152, 5, 333, 10000) |
| 8 | getSupportedVersion → int | – |

`ICastContext` proxy `defpackage/oip.java` (inlined in `oie`): code 6 getDiscoveryManagerImpl → `IDiscoveryManager`;
code 5 getSessionManagerImpl → `ISessionManager`; code 3 addVisibilityChangeListener(IAppVisibilityListener `okf`) [apk].
`IAppVisibilityListener` stub `defpackage/oin.java`: 1 getWrappedThis, 2 onAppEnteredForeground, 3 onAppEnteredBackground, 4 version [apk].
`IDiscoveryManager` proxy `defpackage/ois.java`: code 5 getWrappedThis [apk].

`ISessionManager` proxy `defpackage/oiy.java`: 1 getWrappedCurrentSession → IObjectWrapper; 2 addSessionManagerListener(ISessionManagerListener);
6 endCurrentSession(`writeInt(1)`, `writeInt(stopCasting)`); 7 getWrappedThis [apk].
`ISessionManagerListener` stub `defpackage/oja.java` (reply `writeNoException`): 1 getWrappedThis; 2 onSessionStarting(session);
3 onSessionStarted(session, String sessionId); 4 onSessionStartFailed(session, int); 5 onSessionEnding; 6 onSessionEnded(session, int);
7 onSessionResuming(session, String); 8 onSessionResumed(session, bool); 9 onSessionSuspended(session, int); 10 onSessionResumeFailed(session, int); 11 version [apk].
(Mapping names from the `oji` method order used by `acen`; the semantic names are inferred from YouTube's handler bodies, e.g. case 8 → `acen.d()` resumes and re-registers the namespace.)

`ISession` proxy `defpackage/oiw.java`: 1 getWrappedObject; 5 isConnected → bool; 9 isResuming → bool; 12 notifyFailedToResumeSession? (`writeInt(2151)`);
13 notifySessionEnded(int); 15 notifyFailedToStartSession? (`writeInt(2153)`); 17 getSupportedVersion; 18 getCastState-like int (gated >= 211100000) [apk] – names of 12/15/18 not determined.
`ISessionProxy` stub (`ogn` case 8): 1 getWrappedSession, 2 start(Bundle), 3 resume(Bundle), 4 end(bool), 5 getSessionRemainingTimeMs → long, 6 version, 7/8 (Bundle → `g`/`f`: update CastDevice only), 9 onRouteUpdated(Bundle) → `j` [apk].
`ICastSession` proxy `defpackage/oiq.java` (two-way `ny`): 1 onConnected(null parcelable), 2 onConnectionSuspended(int), 3 onConnectionFailed(ConnectionResult) [unused], 4 onApplicationConnected(ApplicationMetadata, String status, String sessionId, bool wasLaunched), 5 onApplicationConnectionFailed(int), 6 disconnectFromDevice(bool stopCasting, int 0), 7 (bool) [unused] [apk].
`ISessionProvider` stub (`ogn` case 7, from `qkj`): 1 getSession(String sessionId) → IObjectWrapper(new `oil`), 2 isSessionRecoverable → `CastOptions.g`, 3 getCategory → string, 4 version [apk].
`IReconnectionService` proxy `defpackage/oiu.java`: 1 onCreate, 2 onStartCommand(Intent,int,int)→int, 3 onBind(Intent)→IBinder, 4 onDestroy; service class `defpackage/oje.java` [apk].

---

## 9. YouTube custom namespace (`urn:x-cast:com.google.youtube.mdx`)

- Namespace constant: `acesVar.g = "urn:x-cast:com.google.youtube.mdx"` (`castDataChannelNameSpace`) in `defpackage/fvk.java b()`,
  stored as `acet.h`, copied to `aceo.d` and `acrd.d` (`defpackage/aceo.java:56`, `defpackage/acrd.java` ctor) [apk].
  Other config in the same builder: `dialAppName = "YouTube"`, `theme = "cl"`, `castAppIdConfigs = afjr` with main id `233637DE` [apk].
- Registration: on `onSessionStarted`/`onSessionResumed` (`defpackage/acen.java k()`): `oil.c.g(namespace, acem)` →
  `oht.g()` → controller codes 12 then 11 (section 3) [apk].
- Outgoing message (`defpackage/alyt.java p()`): JSON `{"type":"getMdxSessionStatus"}` sent via `oil.l(namespace, json)` → `oht.b()` → controller code 9 [apk].
- Incoming handling (`defpackage/acem.java a(String)`, branch `b == 0`): parses JSON; requires `"type" == "mdxSessionStatus"`;
  reads `data.screenId` and `data.deviceId` (both `getString`, mandatory) and builds the MDX lounge session (`aclo` with `acmi(screenId)`, `aclq(deviceId)`);
  only processed once per session (`acrd.h` flag). Parse failure → `acrd.aE()` (session error) [apk].
- The full MDX message-type vocabulary is in `defpackage/acmd.java` (e.g. `mdxSessionStatus`, `mdxRemoteStatus`, `mdxEncrypted`,
  `getReceiverStatus`, `receiverStatus`, `heartbeat`, …) but only `getMdxSessionStatus`/`mdxSessionStatus` are used on the Cast namespace in code;
  the rest are lounge (HTTP) protocol types [apk]. `loungeToken` is not read from the Cast message (not present in `acem`) [apk].
- The standard media channel `urn:x-cast:com.google.cast.media` (`defpackage/onv.java`, RemoteMediaClient `olv`) is also registered by
  the framework CastSession (`oil.m()` → `olv.m(oht)` / `olv.l()`), and `urn:x-cast:com.google.cast.customdata` (`defpackage/omx.java`) by the relay path [apk].

---

## 10. Open items (not determined from the APK)

1. Names/semantics of `ICastDeviceController` codes 17 and 19 (sent with no params around listener registration), and unused codes 2, 3, 6, 8, 10, 15, 16.
2. Meaning of `GetServiceRequest` boolean field 14 (set when `g()` true) beyond "true for `oni`/`ond`".
3. Exact AIDL method names for ICastService codes 5/6/7 (client calls them "get flags", "dictionary", "integer map" by usage only) and codes 1-4.
4. `ISession` codes 12 (`2151`), 15 (`2153`), 18 – names and the meaning of the int constants.
5. Server-side behaviour expected for listener code 4 (String,double,bool) and 6 (binary) – the client ignores both.
6. What the dynamite module (GMS side) does internally with `IMediaRouter`/route selection to decide `ISessionProxy.start` – not in the APK.
7. Whether `EXTRA_CAST_FLAGS` bits other than 0 are ever used – only `0L` is ever written.
8. Legacy client `onh` ("Cast.API", bundle extras `listener`, `last_application_id`, `last_session_id`) is compiled in but has no live call site; whether any code path reaches it could not be confirmed (only `ohj` static init references it).
9. The receiver-app-id SparseArray (`afjr.b`) is only ever populated via `MdxReceiverAppVersion` preference lookups; alternative app ids are not present as literals in the APK (only `233637DE`).
10. No connect/handshake timeout exists in the client; behaviour on a server that never answers listener code 14 is "wait forever" (as far as the decompiled code shows).
