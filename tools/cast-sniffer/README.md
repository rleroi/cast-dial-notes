# cast-sniffer

Logs CASTV2 traffic as JSONL for `spec/castv2.md` and `spec/youtube-mdx.md`.
Python 3.10+, managed with `uv` (`uv sync` once, then `uv run cast_sniffer.py ...`; `probe_auth.py <host>` sends a deviceauth challenge and prints the response sizes).

## Modes

| Mode | What it gives | Source tag |
|---|---|---|
| `discover` | `_googlecast._tcp` receivers + raw TXT records (`id`, `fn`, `md`, `ca`, `rs`, `ve`, ...) | `[capture]` |
| `watch HOST` | connect as an extra sender; logs receiver/media status broadcasts and whatever the running app sends to all senders | `[capture]` (partial: sender-specific messages of other senders are not visible) |
| `youtube-ref HOST VIDEO_ID` | drive the YouTube receiver (`233637DE`) with pychromecast's YouTubeController: launch, `getMdxSessionStatus`, screen-id handoff, Lounge API playback | `[reference-impl]` |
| `proxy HOST` | TLS man-in-the-middle advertised as a second receiver on this Mac; logs both directions of a **real phone session** decoded | `[capture]` |

All four write `capture-<timestamp>.jsonl` (override with `--log`). Heartbeats are skipped unless `--heartbeat`.

## Capturing a real YouTube cast session (phone with official Play Services)

Needs: Mac on the same Wi-Fi as the Chromecast and the phone, Chromecast IP, `openssl` on PATH.

1. `uv run cast_sniffer.py discover` — note the Chromecast's IP and `id`.
2. `uv run cast_sniffer.py proxy <chromecast-ip> --name "Capture TV"`
   - It copies the Chromecast's TXT record, swaps `id`/`fn`, advertises it from the Mac on port 8009 and forwards to the real device.
   - If something already uses 8009 on the Mac, add `--listen-port 8010`.
3. On the phone (official Play Services + official YouTube): tap Cast, pick **"Capture TV"**, play a video, pause, seek, change volume, add to queue, then disconnect.
4. Ctrl-C. Keep the JSONL. Watch the first records:
   - `c2r` on `urn:x-cast:com.google.cast.tp.deviceauth` = the sender's challenge.
   - `r2c` deviceauth response carries the Chromecast's cert. Official senders verify that this cert matches the TLS peer cert. Because the proxy terminates TLS with its own cert, **the official sender may abort right after deviceauth**. If the log stops after the deviceauth reply, that is a finding in itself (answer to the open question "does the official sender abort on deviceauth failure") and the remaining sequence must come from `youtube-ref` + `watch`.
5. Run `youtube-ref <chromecast-ip> dQw4w9WgXcQ --stop` for the reference-implementation sequence, and `watch` while casting from the phone directly to the real Chromecast to get the broadcast side of a genuine session.

Privacy: the JSONL contains the Lounge token / screen id for your TV and possibly account-bound tokens in `youtube.mdx` payloads. Don't commit raw captures; keep them out of git (`captures/` is ignored) and redact them before sharing.
