#!/usr/bin/env python3
"""CASTV2 sniffer / probe for the GmsCore Cast project.

Sub-commands
  discover                 list _googlecast._tcp receivers and their TXT records
  watch  HOST              connect as an extra sender, log every CASTV2 frame (receiver status,
                           media status, youtube.mdx broadcasts, ...) to a JSONL file
  youtube-ref HOST VIDEO   reference-implementation run: launch YouTube receiver via pychromecast's
                           YouTubeController and log the full message sequence ([reference-impl])
  proxy  HOST              TLS man-in-the-middle: advertise a fake receiver on this machine that
                           forwards to HOST:8009 and logs both directions decoded ([capture])

Every logged record is one JSON object per line:
  {"t": epoch, "dir": "tx|rx|c2r|r2c", "src": ..., "dst": ..., "ns": ..., "type": "STRING|BINARY",
   "json": <decoded payload or null>, "utf8": <raw text if not json>, "b64": <binary payload>,
   "deviceauth": <decoded DeviceAuthMessage if ns is deviceauth>}
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

import pychromecast
from pychromecast import cast_channel_pb2 as pb
from pychromecast import socket_client as sc
from pychromecast.controllers.youtube import YouTubeController
from pychromecast.discovery import CastBrowser, SimpleCastListener
from zeroconf import IPVersion, ServiceInfo, Zeroconf

NS_DEVICEAUTH = "urn:x-cast:com.google.cast.tp.deviceauth"
NS_HEARTBEAT = "urn:x-cast:com.google.cast.tp.heartbeat"
LOG = logging.getLogger("cast-sniffer")


# ----------------------------------------------------------------------------- logging
class JsonlLog:
    def __init__(self, path: str, skip_heartbeat: bool):
        self.path = path
        self.skip_heartbeat = skip_heartbeat
        self._fh = open(path, "a", encoding="utf-8")
        self._lock = threading.Lock()

    def record(self, direction: str, msg: pb.CastMessage) -> None:
        if self.skip_heartbeat and msg.namespace == NS_HEARTBEAT:
            return
        rec: dict[str, Any] = {
            "t": round(time.time(), 3),
            "dir": direction,
            "src": msg.source_id,
            "dst": msg.destination_id,
            "ns": msg.namespace,
            "type": "BINARY" if msg.payload_type == pb.CastMessage.BINARY else "STRING",
        }
        if msg.payload_type == pb.CastMessage.STRING:
            try:
                rec["json"] = json.loads(msg.payload_utf8)
            except ValueError:
                rec["utf8"] = msg.payload_utf8
        else:
            rec["b64"] = base64.b64encode(msg.payload_binary).decode()
            if msg.namespace == NS_DEVICEAUTH:
                rec["deviceauth"] = decode_deviceauth(msg.payload_binary)
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()
        LOG.info("%s %s -> %s %s %s", direction, msg.source_id, msg.destination_id, msg.namespace,
                 (json.dumps(rec.get("json")) if "json" in rec else rec.get("utf8") or f"<binary {len(msg.payload_binary)}B>")[:300])


def decode_deviceauth(raw: bytes) -> dict[str, Any]:
    m = pb.DeviceAuthMessage()
    try:
        m.ParseFromString(raw)
    except Exception as exc:  # noqa: BLE001
        return {"parse_error": str(exc)}
    out: dict[str, Any] = {}
    if m.HasField("challenge"):
        c = m.challenge
        out["challenge"] = {"signature_algorithm": c.signature_algorithm, "hash_algorithm": c.hash_algorithm,
                            "sender_nonce_b64": base64.b64encode(c.sender_nonce).decode()}
    if m.HasField("response"):
        r = m.response
        out["response"] = {"signature_len": len(r.signature), "signature_algorithm": r.signature_algorithm,
                           "hash_algorithm": r.hash_algorithm,
                           "sender_nonce_b64": base64.b64encode(r.sender_nonce).decode(),
                           "client_auth_certificate_der_b64": base64.b64encode(r.client_auth_certificate).decode(),
                           "intermediate_certificates": len(r.intermediate_certificate),
                           "crl_len": len(r.crl)}
    if m.HasField("error"):
        out["error"] = {"error_type": m.error.error_type}
    return out


# ----------------------------------------------------------------------------- pychromecast hooks
def install_pychromecast_hooks(log: JsonlLog) -> None:
    """Log every frame pychromecast reads or writes, regardless of namespace handlers."""
    orig_read = sc.SocketClient._read_message
    orig_send = sc.SocketClient.send_message

    def _read_message(self):
        msg = orig_read(self)
        log.record("rx", msg)
        return msg

    # send_message builds the proto internally; re-create a copy for the log.
    def send_message(self, destination_id, namespace, data, *args, **kwargs):
        result = orig_send(self, destination_id, namespace, data, *args, **kwargs)
        msg = pb.CastMessage()
        msg.protocol_version = msg.CASTV2_1_0
        msg.source_id = self.source_id
        msg.destination_id = destination_id
        msg.namespace = namespace
        msg.payload_type = pb.CastMessage.STRING
        msg.payload_utf8 = json.dumps(data)
        log.record("tx", msg)
        return result

    sc.SocketClient._read_message = _read_message
    sc.SocketClient.send_message = send_message


def connect_host(host: str, port: int) -> pychromecast.Chromecast:
    cast = pychromecast.get_chromecast_from_host((host, port, None, None, None), tries=1)
    cast.wait(timeout=15)
    LOG.info("connected: %s model=%s status=%s", cast.cast_info.friendly_name, cast.cast_info.model_name, cast.status)
    return cast


# ----------------------------------------------------------------------------- commands
def cmd_discover(args: argparse.Namespace) -> None:
    zc = Zeroconf()
    seen: dict[str, Any] = {}

    def add(uuid, service):
        info = browser.devices.get(uuid)
        if info and uuid not in seen:
            seen[uuid] = info
            print(json.dumps({"uuid": str(uuid), "host": info.host, "port": info.port,
                              "friendly_name": info.friendly_name, "model": info.model_name,
                              "manufacturer": info.manufacturer, "cast_type": info.cast_type,
                              "services": sorted(str(s) for s in info.services)}, ensure_ascii=False))

    browser = CastBrowser(SimpleCastListener(add), zc)
    browser.start_discovery()
    time.sleep(args.seconds)
    browser.stop_discovery()
    zc.close()
    # Raw TXT records via zeroconf, for the spec
    zc = Zeroconf()
    try:
        for uuid, info in seen.items():
            name = f"{info.uuid}._googlecast._tcp.local." if info.uuid else None
            if name:
                si = zc.get_service_info("_googlecast._tcp.local.", name, timeout=3000)
                if si:
                    txt = {k.decode(): (v.decode(errors="replace") if v else "") for k, v in si.properties.items()}
                    print(json.dumps({"uuid": str(uuid), "txt": txt}, ensure_ascii=False))
    finally:
        zc.close()


def cmd_watch(args: argparse.Namespace) -> None:
    log = JsonlLog(args.log, not args.heartbeat)
    install_pychromecast_hooks(log)
    cast = connect_host(args.host, args.port)
    # Join whatever app is running so broadcast messages on its transport reach us.
    yt = YouTubeController()
    cast.register_handler(yt)
    LOG.info("watching; Ctrl-C to stop. Logging to %s", log.path)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cast.disconnect()


def cmd_youtube_ref(args: argparse.Namespace) -> None:
    log = JsonlLog(args.log, not args.heartbeat)
    install_pychromecast_hooks(log)
    cast = connect_host(args.host, args.port)
    yt = YouTubeController()
    cast.register_handler(yt)
    LOG.info("launching YouTube receiver and playing %s", args.video_id)
    yt.play_video(args.video_id)
    LOG.info("screen_id=%s", yt._screen_id)  # noqa: SLF001
    try:
        time.sleep(args.seconds)
    except KeyboardInterrupt:
        pass
    finally:
        if args.stop:
            cast.quit_app()
            time.sleep(2)
        cast.disconnect()


# ----------------------------------------------------------------------------- proxy
def _read_frame(sock: socket.socket) -> pb.CastMessage | None:
    hdr = b""
    while len(hdr) < 4:
        chunk = sock.recv(4 - len(hdr))
        if not chunk:
            return None
        hdr += chunk
    (length,) = struct.unpack(">I", hdr)
    body = b""
    while len(body) < length:
        chunk = sock.recv(length - len(body))
        if not chunk:
            return None
        body += chunk
    msg = pb.CastMessage()
    msg.ParseFromString(body)
    return msg


def _write_frame(sock: socket.socket, msg: pb.CastMessage) -> None:
    body = msg.SerializeToString()
    sock.sendall(struct.pack(">I", len(body)) + body)


def _pump(src: socket.socket, dst: socket.socket, direction: str, log: JsonlLog, stop: threading.Event) -> None:
    try:
        while not stop.is_set():
            msg = _read_frame(src)
            if msg is None:
                break
            log.record(direction, msg)
            _write_frame(dst, msg)
    except (OSError, ssl.SSLError) as exc:
        LOG.info("%s closed: %s", direction, exc)
    finally:
        stop.set()
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _self_signed_cert(dirpath: str) -> tuple[str, str]:
    crt, key = os.path.join(dirpath, "proxy.crt"), os.path.join(dirpath, "proxy.key")
    if not os.path.exists(crt):
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                        "-days", "30", "-subj", "/CN=cast-sniffer-proxy"], check=True, capture_output=True)
    return crt, key


def _fetch_target_txt(target_host: str, port: int, seconds: float) -> tuple[dict[str, bytes], str | None]:
    """Find the target's _googlecast._tcp record by IP and return (TXT properties, service name)."""
    zc = Zeroconf()
    found: dict[str, Any] = {}

    def add(uuid, service):
        info = browser.devices.get(uuid)
        if info and info.host == target_host:
            found["uuid"] = info.uuid

    browser = CastBrowser(SimpleCastListener(add), zc)
    browser.start_discovery()
    deadline = time.time() + seconds
    while "uuid" not in found and time.time() < deadline:
        time.sleep(0.2)
    browser.stop_discovery()
    props: dict[str, bytes] = {}
    name = None
    if "uuid" in found:
        name = f"{found['uuid']}._googlecast._tcp.local."
        si = zc.get_service_info("_googlecast._tcp.local.", name, timeout=3000)
        if si:
            props = dict(si.properties)
    zc.close()
    return props, name


def _local_ip(target_host: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((target_host, 9))
    ip = s.getsockname()[0]
    s.close()
    return ip


def cmd_proxy(args: argparse.Namespace) -> None:
    log = JsonlLog(args.log, not args.heartbeat)
    props, name = _fetch_target_txt(args.host, args.port, 8)
    if not props:
        LOG.error("could not find the target's mDNS record; is %s a Cast receiver on this LAN?", args.host)
        sys.exit(1)
    txt = {k.decode(): v for k, v in props.items()}
    LOG.info("target TXT: %s", {k: (v.decode(errors='replace') if v else '') for k, v in txt.items()})

    # Advertise a copy with a distinct id/name so both the real device and the proxy show up.
    orig_id = txt.get("id", b"").decode()
    proxy_id = (args.id or ("f" * 8 + orig_id[8:])) if orig_id else "f" * 32
    txt["id"] = proxy_id.encode()
    txt["fn"] = (args.name or (txt.get("fn", b"receiver").decode() + " (proxy)")).encode()
    local_ip = _local_ip(args.host)
    svc_name = f"{proxy_id}._googlecast._tcp.local."
    info = ServiceInfo("_googlecast._tcp.local.", svc_name, addresses=[socket.inet_aton(local_ip)],
                       port=args.listen_port, properties=txt, server=f"{proxy_id}.local.")
    zc = Zeroconf(ip_version=IPVersion.V4Only)
    zc.register_service(info)
    LOG.info("advertising '%s' id=%s at %s:%d -> %s:%d", txt["fn"].decode(), proxy_id, local_ip, args.listen_port,
             args.host, args.port)

    crt, key = _self_signed_cert(args.cert_dir)
    srv_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    srv_ctx.load_cert_chain(crt, key)
    cli_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cli_ctx.check_hostname = False
    cli_ctx.verify_mode = ssl.CERT_NONE

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", args.listen_port))
    listener.listen(8)
    LOG.info("proxy listening; select '%s' on the phone. Ctrl-C to stop. Log: %s", txt["fn"].decode(), log.path)

    def handle(conn: socket.socket, peer):
        LOG.info("sender connected from %s", peer)
        try:
            tls_in = srv_ctx.wrap_socket(conn, server_side=True)
        except ssl.SSLError as exc:
            LOG.warning("TLS handshake with sender failed: %s", exc)
            conn.close()
            return
        upstream = cli_ctx.wrap_socket(socket.create_connection((args.host, args.port), timeout=10))
        upstream.settimeout(None)
        stop = threading.Event()
        threading.Thread(target=_pump, args=(tls_in, upstream, "c2r", log, stop), daemon=True).start()
        threading.Thread(target=_pump, args=(upstream, tls_in, "r2c", log, stop), daemon=True).start()

    try:
        while True:
            conn, peer = listener.accept()
            threading.Thread(target=handle, args=(conn, peer), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        zc.unregister_service(info)
        zc.close()
        listener.close()


# ----------------------------------------------------------------------------- main
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-v", "--verbose", action="store_true", help="also enable pychromecast debug logging")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover")
    d.add_argument("--seconds", type=float, default=5)
    d.set_defaults(func=cmd_discover)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("host")
    common.add_argument("--port", type=int, default=8009)
    common.add_argument("--log", default=f"capture-{time.strftime('%Y%m%d-%H%M%S')}.jsonl")
    common.add_argument("--heartbeat", action="store_true", help="also log heartbeat PING/PONG")

    w = sub.add_parser("watch", parents=[common])
    w.set_defaults(func=cmd_watch)

    y = sub.add_parser("youtube-ref", parents=[common])
    y.add_argument("video_id")
    y.add_argument("--seconds", type=float, default=30)
    y.add_argument("--stop", action="store_true", help="stop the receiver app at the end")
    y.set_defaults(func=cmd_youtube_ref)

    x = sub.add_parser("proxy", parents=[common])
    x.add_argument("--listen-port", type=int, default=8009)
    x.add_argument("--name", help="friendly name to advertise (default: '<target fn> (proxy)')")
    x.add_argument("--id", help="32-hex receiver id to advertise (default: target id with first 8 chars = f)")
    x.add_argument("--cert-dir", default=tempfile.gettempdir())
    x.set_defaults(func=cmd_proxy)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not args.verbose:
        logging.getLogger("pychromecast").setLevel(logging.WARNING)
        logging.getLogger("zeroconf").setLevel(logging.WARNING)
    args.func(args)


if __name__ == "__main__":
    main()
