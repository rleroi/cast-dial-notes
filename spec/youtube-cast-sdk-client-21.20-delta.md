# YouTube 21.20.405 vs 19.17.42 – Cast client SDK delta (as seen from the APK)

Source: jadx decompilation of YouTube 21.20.405 (jadx output, `sources/`). Paths are relative to that
root; obfuscated names are the 21.20 names (they differ from the 19.17 report). Every fact is tagged `[apk]`.
Base report: `youtube-cast-sdk-client.md` (19.17.42); section numbers below follow it.

AIDL helper renames (`defpackage/hdi.java`, `defpackage/hdk.java`) [apk]: proxy base `hdi`: `D()` = obtain +
`writeInterfaceToken`; `E(code,p)` = two-way with reply; `F(code,p)` = two-way void; `G(code,p)` =
`transact(code, p, null, FLAG_ONEWAY=1)` → **oneway**. Stub base `hdj.H(code, in, out)`. `hdk.c` = write nullable
Parcelable (int 0 / int 1 + writeToParcel), `hdk.e` = writeStrongBinder, `hdk.a` = read nullable Parcelable,
`hdk.b` = enforceNoDataAvail (throws `BadParcelableException` if unread data remains), `hdk.f` = readInt != 0.

---

## 1. SDK identification – CHANGED

| Item | 19.17 | 21.20 | Evidence |
|---|---|---|---|
| cast-framework version string | `"21.5.0"` | **`"22.3.2"`** | `defpackage/rcf.java:15` (`b = "22.3.2"`), `defpackage/rca.java:26`, `defpackage/rbz.java:12`, `defpackage/aegn.java:460` (written into analytics proto) [apk] |
| GMS client-library version code | `241802000` | **`262105000`** | `defpackage/rjs.java:18` (`c = 262105000`); returned by every client stub "getSupportedVersion" (e.g. `defpackage/rcm.java:83` IMediaRouter code 10, `defpackage/raw.java` ISessionProxy code 6, ICastConnectionController code 5) [apk] |
| Manifest `com.google.android.gms.version` check | `241802000` | must equal `262105000` else `GooglePlayServicesIncorrectManifestValueException` (own manifest, not GMS) | `defpackage/rkj.java:73-79` [apk] |
| Dynamite module id / impl class / descriptor | same | unchanged: `"com.google.android.gms.cast.framework.dynamite"`, `CastDynamiteModuleImpl`, `ICastDynamiteModule` | `defpackage/rcj.java:18-22` [apk] |
| Version policy | remote-first (`oxe(1)`) | unchanged: `rsv.a = new rsp(1)` → remote version via chimera content provider first (`!= 0` → remote), else local | `defpackage/rsv.java:36,538`, `defpackage/rsp.java:34-46` [apk] |
| `getMinApkVersion` | 12800000 / 19390000 / 12451000 | unchanged: `rfv` (legacy) 12800000, `rfw` (CXLESS) 19390000, `rfr` (CastApi 161) 12451000; new `rag` (first-party, 122) 12451000 | `defpackage/rfv.java:73`, `rfw.java:36`, `rfr.java:22`, `rag.java:22` [apk] |
| Gates on dynamite-served interfaces | ISession ≥211100000, IMediaRouterCallback ≥220400000 | unchanged plus **new `IMediaRouterCallback.getSupportedVersion() >= 251600000`** gate for codes 9/10 (route connected/disconnected) | `defpackage/rbo.java:58`, `defpackage/rcq.java:70,103,167` [apk] |
| Dynamic bind lookup | off (`a() >= 211700000` false) | unchanged (`rob.f()`: `a() >= 211700000`, false for all cast clients) | `defpackage/rob.java:266-268` [apk] |

---

## 2. Service binding – MOSTLY UNCHANGED, one new client

### 2.1 Clients present

| Client | service id | action | descriptor | status |
|---|---|---|---|---|
| `defpackage/rfw.java` `"CastClientImplCxless"` | 10 | `…cast.service.BIND_CAST_DEVICE_CONTROLLER_SERVICE` | `…cast.internal.ICastDeviceController` | unchanged; used by `defpackage/qzo.java` (`"Cast.API_CXLESS"`, line 45) [apk] |
| `defpackage/rfv.java` `"CastClientImpl"` (legacy) | 10 | same | same | unchanged, still dead: only `new rfv(` is `defpackage/qyw.java:20`, whose API object `new bpv("Cast.API", …)` in `defpackage/qyz.java:12` is discarded; still accepts status 2300 (`rfv.java:166-175`) [apk] |
| `defpackage/rfr.java` | 161 | same action | `…cast.internal.ICastService` | unchanged (`"CastApi.API"`) [apk] |
| **NEW** `defpackage/rag.java` | **122** | **`com.google.android.gms.cast.firstparty.START`** | **`com.google.android.gms.cast.firstparty.internal.ICastFirstPartyService`** | API `"CastFirstParty.API"` (`defpackage/rae.java:14`, `rad.java:15`); requests the same 15 features (`rag.g()` = `qzg.p`) [apk] |

### 2.2 Bind mechanics – unchanged (`defpackage/rob.java`)
`GetServiceRequest` = `rop` (`defpackage/rop.java`, writer `defpackage/jbt.java:25-70`): built in `rob.z()`
(`rob.java:365-397`) as `rop(6, serviceId, 262105000, …, true, 0, false, attributionTag)`; `f` = package name (4),
`i` = extras `h()` (7), `k` = `P()` required features (10), `l` = `g()` api features (11), field 14 (`o`) = `S()` → true for
`rfw`, `rfr`, `rag` (each overrides `S()` to return true; `rfv` not). Sent as broker transaction **46** with
`IGmsCallbacks` stub `rpf` (`rob.java:404-411`) [apk]. Post-init status handling unchanged (status 0 required for CXLESS).

### 2.3 Extras bundle `h()` – CHANGED (one new key)
`rfw.h()` (`defpackage/rfw.java:60-72`): `CastDevice.f(bundle)` → `com.google.android.gms.cast.EXTRA_CAST_DEVICE`
(`CastDevice.java:141`), `EXTRA_CAST_FLAGS` = `0L`, `connectionless_client_record_id` = string, plus caller bundle [apk].
Caller bundle from framework `CastSession` `defpackage/ras.java:108-111` now has **four** booleans:
`EXTRA_CAST_FRAMEWORK_NOTIFICATION_ENABLED`, `EXTRA_CAST_REMOTE_CONTROL_NOTIFICATION_ENABLED`,
`EXTRA_CAST_ALWAYS_FOLLOW_SESSION_ENABLED` and **new `com.google.android.gms.cast.EXTRA_USE_ROUTE_CONNECTION`** =
`rcs.i`, which is set true only in `IMediaRouterCallback` "onRouteConnected" (`defpackage/rcq.java:67`) and false on
disconnect (`rcq.java:100`); default false (`defpackage/rcs.java:26`) [apk]. `ras.java:125` also reads
`com.google.android.gms.cast.EXTRA_WAKE_ON_LAN_STATE` (int) from a session bundle [apk].
`rfr.h()`/`rag.h()` not overridden → empty Bundle (`rob.java:278`) [apk]. Legacy `rfv.h()` unchanged (`listener`,
`last_application_id`, `last_session_id`, `rfv.java:97-111`).

### 2.4 Requested API features – CHANGED (15)
`defpackage/qzg.java:23-56`: the 13 of 19.17 plus **`device_suggestions`** (`qzg.n`) and
**`cxless_connect_with_options`** (`qzg.o`), all version 1; array `qzg.p` returned by `rfw.g()`, `rfr.g()`, `rag.g()` [apk].
Per-call requirements: `qzg.b` (cxless_client_minimal) for listener registration in `qzo.d()` (`qzo.java:127`);
**`qzg.o` for the connect-with-options registration** in `defpackage/rfc.java:233`; `qzg.n` is **never referenced
individually** (grep: only `qzg.java`) → `device_suggestions` is declared at bind only [apk].

---

## 3. `ICastDeviceController` proxy (`defpackage/rgd.java` + inlined call sites) – CHANGED

Two structural changes: (a) **every transaction now appends an `ApiMetadata` SafeParcel** (`rku`, written with
`hdk.c(parcel, rqq.m())`) as the LAST parameter; (b) **new code 21** (connect with options). All calls still `G()` = oneway [apk].

`ApiMetadata` (`defpackage/rku.java:55-66`): `writeInt(-204102970)` magic, then SafeParcel header 20293 with field 1 =
`ComplianceOptions` (`defpackage/rkw.java`: fields 1 callerProductId=-1, 2 dataOwnerProductId=-1, 3 processingReason=0,
4 isUserData=true) and field 2 bool = false (`rqq.o()`, `defpackage/rqq.java:928-930`) [apk]. A server that reads the
old parameter list and then calls `enforceNoDataAvail` would throw; one that ignores trailing data is fine.

| Code | Params (in order, all followed by `hdk.c(ApiMetadata)`) | Call site |
|---|---|---|
| 1 disconnect | – | `rgd.a()`; `rfw.l()` on client disconnect (`rfw.java:76`); 8403 `qzi(0)` [apk] |
| 4 leave application | – | `defpackage/qzl.java` case 0 (relay path, from `rfc`) [apk] |
| 5 stopApplication | `writeString(sessionId)` | `defpackage/qxw.java` case 3 (8409) [apk] |
| 7 setVolume | `writeDouble(level)`, `writeDouble(current)`, `writeInt(muted)` | `defpackage/akrl.java:239-246` (8411) [apk] |
| 9 sendMessage | `writeString(ns)`, `writeString(msg)`, `writeLong(requestId)` | `defpackage/qzj.java` case 2 (8405), limit 524288 (`qzo.java:102`) [apk] |
| 11 registerNamespace | `writeString(ns)` | `qzj` case 3 (8413), after 12 [apk] |
| 12 unregisterNamespace | `writeString(ns)` | `rgd.h()`; `qzj` case 0 (8414) / case 3 [apk] |
| 13 launchApplication | `writeString(appId)`, `hdk.c(LaunchOptions qzq)` | `qzj` case 1 (8406) [apk] |
| 14 joinApplication | `writeString(appId)`, `writeString(sessionId)`, `hdk.c(JoinOptions qzp)` | `qzo.a()` (8407, `qzo.java:76-88`) [apk] |
| 17 connect (legacy) | – | `qzl` case 1, sent right after 18; **still used by the framework CastSession path** (`ras.java:120` → `qzo.d()`, `qzo.java:118-130`) [apk] |
| 18 registerListener | `hdk.e(listener stub)` | `rgd.b()`; `qzl` case 1 and `qxw` case 4 [apk] |
| 19 unregisterListener | – | `rgd.g()`; `qzi` cases 2/3 (8415) [apk] |
| **21 connectWithOptions (NEW)** | **`hdk.c(ConnectOptions qzc)`** then ApiMetadata | `qxw` case 4 (`qxw.java:84-92`): 18 then 21; registered under key `castDeviceControllerListenerKey`, method 8428, required feature `cxless_connect_with_options` (`rfc.java:223-235`) [apk] |

`ConnectOptions` `defpackage/qzc.java`: SafeParcel with single field 1 int `connectionType`, allowed values 0
(`"STRONG"`) or 2 (`"INVISIBLE"`); `rfc.java:224` uses `new qzc(2)` = INVISIBLE [apk].
Which path runs: `rfc.b()` (relay/"RemoteConnectionManager"-style path, created by YouTube's `defpackage/akeq.java:56`)
uses 18+21 only if `rfc.m` (`rfi.k`) is true; `rfi.k` is set from the ICastService flag Bundle key
**`com.google.android.gms.cast.FLAG_ENABLE_CONNECT_WITH_OPTIONS`** (default false) (`defpackage/rfd.java:21`);
otherwise `qzo.d()` → 18+17 [apk]. So on a server that does not return that flag, code 21 is never sent.
Codes 2, 3, 6, 8, 10, 15, 16, 20 are not used (grep `.G(` over rgd users) [apk]. No "getClientInfo" call exists.

---

## 4. `ICastDeviceControllerListener` stub (`defpackage/rge.java`) – UNCHANGED
Codes 1-15 with identical parameter lists to 19.17 (`rge.java:14-104`); no code ≥16; no reply written (oneway-style);
each case ends with `hdk.b(parcel)` (enforceNoDataAvail) → the server must NOT append ApiMetadata to listener calls [apk].
Implementation `defpackage/qzn.java` (CXLESS): 14 → `h(int)` posts `lje(…,13)` (connect result), 15 → `k(int)` posts
`lje(…,15)` (suspended), 1 → `j(int)` disconnected (`qzn.java:59-77`) – same semantics as 19.17 [apk].

---

## 5. `ICastService` (161) – UNCHANGED codes, ApiMetadata appended, one new flag
`defpackage/rfl.java:22-50`: code 7 (`writeStrongBinder(IBundleCallback)`, `writeStringArray`, ApiMetadata) and code 5
(same shape); `defpackage/qzl.java` case 2: code 6 (`hdk.e(callback)`, `writeStringArray`, ApiMetadata) [apk].
`IBundleCallback` stub `defpackage/rgb.java`: code 1 `hdk.a(Bundle)` + `hdk.b` – unchanged [apk].
Flag names requested via code 5 (grep): the 7 analytics flags of 19.17 (`defpackage/rcs.java`/analytics class lines 170-201),
`FLAG_OUTPUT_SWITCHER_ENABLED` + **new `FLAG_SHOW_SYSTEM_OUTPUT_SWITCHER_ON_CAST_ICON_CLICK`** (`rcs.java:40`, both read as
boolean in `defpackage/rap.java:45-52`), and **new `FLAG_ENABLE_CONNECT_WITH_OPTIONS`** (boolean, `rfd.java:21`) [apk].
Dictionary/map names for codes 6/7 unchanged (`DICTIONARY_CAST_STATUS_CODES_TO_APP_SESSION_ERROR`,
`…_CHANGE_REASON`, `MAP_CAST_STATUS_CODES_TO_CAST_REASON_CODES`) [apk].

**NEW `ICastFirstPartyService` (service 122)** proxy `defpackage/rah.java`: code **2** = `hdk.e(ICastSettingsCallback stub)`,
ApiMetadata; callback descriptor `com.google.android.gms.cast.firstparty.internal.ICastSettingsCallback`, code 1 reads
`Bundle` + `ApiMetadata` (`defpackage/raw.java:40-44,126-133`). Called from YouTube's MdxMediaRouteChooserDialog
`defpackage/akly.java:75-93` (method id 8417) **only if `rjs.l(context, 211500000) == 0`** (GMS available ≥ 211500000);
otherwise it short-circuits with `ryt.z(2)`. This is the `get_cast_settings` feature; no bundle keys are read in `akly`
(result only forwarded) [apk]. Nothing in the APK sends a request specifically for `device_suggestions`.

---

## 6. Connection handshake – unchanged for the framework path
`ras.java:95-121`: `qzo` built with the 4-key bundle, `qzo.d()` → 18 then 17, waits for listener 14 → ICastSession code 1
(`defpackage/ray.java:65`); launch/join via ICastConnectionController stub (`raw` variant 0, `raw.java:60-120`, codes 1-5,
code 5 returns 262105000) → controller 14/13; ICastSession codes 4/5/6/2 as before (`ray.java`) [apk].
ISession proxy `defpackage/rbe.java`: codes 1, 5, 9, 12 (`writeInt(2151)`), 13, 15 (`writeInt(2153)`), 17, 18 (gated ≥211100000) – unchanged [apk].
ICastDynamiteModule proxy `defpackage/rck.java`: codes 1, 2, 3, 5, 6, 7, 8 – unchanged [apk]. No client-side timeout found.

---

## 7. MediaRouter side – CHANGED (new IMediaRouter/IMediaRouterCallback codes), strings unchanged
- Category builder `defpackage/bpv.java:234,690-716`: `"com.google.android.gms.cast.CATEGORY_CAST" + "/" + appId [+ "/" ns…]`,
  trailing `"/"` when no namespaces, suffix `"//ALLOW_IPV6"` – unchanged. App id `"233637DE"` (`defpackage/akex.java:9`,
  `akrv.java:52`, `atyl.java:71`); MDX category `"MDX_MEDIA_ROUTE_CONTROL_CATEGORY_" + theme` (`defpackage/hiq.java:5047`);
  selector bundle key `"controlCategories"` (`defpackage/eez.java:35`, `hbb.java:187`) [apk].
- Route extras keys: `EXTRA_CAST_DEVICE` (`CastDevice.java:87`), `EXTRA_RUNNING_RECEIVER_APP_ID` (`defpackage/rfh.java:38`, `rfi.java:81`) – unchanged [apk].
- `IMediaRouter` stub `defpackage/rcm.java`: codes 1-13 as in 19.17 plus **new code 14 `(String routeId)`** → `rcs.e(String)`
  (`rcs.java:74-93`: if the selected route has that id and is not the default, `MediaRouter.unselect(0)`) [apk].
- `IMediaRouterCallback` proxy `defpackage/rco.java`: 1 onRouteAdded, 2 onRouteChanged, 3 onRouteRemoved, 4 onRouteSelected(legacy),
  6 onRouteUnselected(id, extras, reason), 7 getSupportedVersion, 8 onRouteSelected(selectedId, routeId, extras) (≥220400000),
  **new 9 `(String, String, Bundle)` onRouteConnected and 10 `(String, String, Bundle, int)` onRouteDisconnected** (used when
  version ≥ 251600000, `rcq.java:70-74,103-107`) [apk].
- `CastDevice` SafeParcel (`CastDevice.java:208-227`): fields 2-19 as before plus **20 Boolean** (`q`, overrides capability-bit-2
  check in `l()`, line 169-175) and **21 Parcelable `android.net.Network`** (`r`) [apk].

---

## 8. cast-framework / CastOptions – CHANGED (fields 19, 20 added)
OptionsProvider meta-data key unchanged (`defpackage/raj.java:393-404`); class
`com/google/android/libraries/youtube/mdx/castclient/CastOptionsProvider.java` builds `ram` (= CastOptions) with the 18-arg ctor
(`defpackage/ram.java:45-66`); SafeParcel layout `ram.writeToParcel` (`ram.java:79-141`) [apk]:

| id | type | YouTube value (CastOptionsProvider.java:24-35) |
|---|---|---|
| 2 | String receiverApplicationId | `castAppId` (`"233637DE"`) |
| 3 | StringList namespaces | empty |
| 4 | bool stopReceiverApplicationWhenEndingSession | false |
| 5 | LaunchOptions `qzq` | `a=false` (relaunchIfRunning), `c = mdxConfig.ao()` (androidReceiverCompatible) |
| 6 | bool resumeSavedSession | `!mdxConfig.af()` |
| 7 | CastMediaOptions `rdb` | builder default (`ram.c` fallback) |
| 8 | bool enableReconnectionService | `!mdxConfig.af()` |
| 9 | double volumeDelta | 0.05 |
| 10, 11 | bool, bool | false, false |
| 12 | bool (output switcher) | `mdxMediaTransferReceiverEnabler.b()` |
| 13 | StringList routeDiscoveryReceiverApplicationIds | empty |
| 14 | bool (remote-to-local) | `mdxMediaTransferReceiverEnabler.b()` |
| 15 | int | always 0 (`ram.java:128-129`) |
| 16 | bool | false |
| 17 | `rak` CastExperimentOptions: SafeParcel field 2 bool | `new rak(mdxConfig.ad())` (`defpackage/rak.java`) |
| 18 | `ral` CastFeatureVersions: SafeParcel field 2 int | `ram.b = ral(0)`, overwritten to `ral(1)` in `raj.java:81` |
| **19** | **bool** (`r`) | **false** (ctor arg 17) |
| **20** | **bool** (`s`) | **false** (ctor arg 18) |

Names of 19/20 are not recoverable from the APK (plain booleans, never read by YouTube code); both are always false [apk].

---

## 9. youtube.mdx namespace – UNCHANGED
Namespace `"urn:x-cast:com.google.youtube.mdx"` (`defpackage/akex.java:11`; used in `ras.java:363`). Outgoing
`{"type":"getMdxSessionStatus"}` (`defpackage/akwh.java:465`). Incoming handler `defpackage/akes.java:32-62`: requires
`type == "mdxSessionStatus"`, reads `data.screenId` and `data.deviceId` (mandatory `getString`), processed once per
session (`akrl.f`); parse failure → `akrl.aL()`. `loungeToken` is still only parsed by the HTTP ScreenInfoParser
(`defpackage/akon.java:56`), not from the Cast message [apk].

---

## 10. GMS package signature / version checks relevant to microG
- `GoogleApiAvailability.isGooglePlayServicesAvailable` (`defpackage/rkj.java:48-140`, called via `rjs.l`) checks the
  `com.google.android.gms` package **signature** (`rkk.d(packageInfo, true)`, line ~107) and `versionCode >= requested`.
  In the Cast code it is only invoked by `akly.java:80` with `211500000` to decide whether to query
  `ICastFirstPartyService` code 2 (cast settings for the chooser dialog); failure degrades gracefully (`ryt.z(2)`) [apk].
- The GmsClient bind path (`rob`) does not verify the GMS signature itself; it only requires the bound binder's
  `getInterfaceDescriptor()` to match and `getMinApkVersion()` (19390000 for CXLESS) – unchanged from 19.17 [apk].
- No cxless-specific minimum gmsVersion exists; the only new gates are IMediaRouterCallback ≥ 251600000 (optional codes 9/10)
  and the 211500000 chooser-dialog check above [apk].

---

## Summary (10 lines)
1. SDK string 21.5.0 → **22.3.2**; GMS client version code 241802000 → **262105000** (`rcf.java`, `rjs.java`).
2. Every `ICastDeviceController`/`ICastService`/`ICastFirstPartyService` call now appends a trailing **ApiMetadata** SafeParcel (`rku`, magic -204102970) – servers must tolerate extra trailing parcel data.
3. Controller codes 1, 4, 5, 7, 9, 11, 12, 13, 14, 17, 18, 19 unchanged; **new code 21 connectWithOptions(ConnectOptions{connectionType int: 0 STRONG / 2 INVISIBLE})**, sent after 18 instead of 17.
4. Code 21 is gated by feature `cxless_connect_with_options` AND the ICastService flag `FLAG_ENABLE_CONNECT_WITH_OPTIONS` (default false); the framework CastSession path still uses 18+17 (`ras.java:120`).
5. Listener stub codes 1-15 unchanged, no new codes; listener cases enforceNoDataAvail (do not append ApiMetadata to them).
6. `device_suggestions` is declared at bind only; nothing in the APK references it individually. `get_cast_settings` maps to new service 122 (`cast.firstparty.START`, `ICastFirstPartyService` code 2 → `ICastSettingsCallback` code 1 Bundle), used only when GMS ≥ 211500000.
7. ICastService codes 5/6/7 unchanged; new flag names `FLAG_SHOW_SYSTEM_OUTPUT_SWITCHER_ON_CAST_ICON_CLICK`, `FLAG_ENABLE_CONNECT_WITH_OPTIONS`.
8. GetServiceRequest extras for service 10 gain `EXTRA_USE_ROUTE_CONNECTION` (bool, false unless a route-connection callback fired); service 161/122 extras empty.
9. CastOptions gains fields **19 and 20 (both bool, always false)**; 17 = CastExperimentOptions{bool}, 18 = CastFeatureVersions{int=1}; CastDevice gains fields 20 (Boolean) and 21 (Network).
10. youtube.mdx message types/keys and MediaRouter category strings unchanged; only new signature/version check is `isGooglePlayServicesAvailable(211500000)` in the chooser dialog (graceful fallback) – nothing else would hard-fail on microG.
