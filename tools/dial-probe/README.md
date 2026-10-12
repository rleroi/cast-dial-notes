# dial-probe

Minimal DIAL receiver (Python standard library only) that makes a computer show up in the YouTube app's cast list and logs
every request the phone makes. On launch it registers the received pairing code with the YouTube Lounge service for a fresh
screen id, which is the step a TV app has to perform.

```
python3 dial_probe.py --name "DIAL test" --port 8060
```

Needs UDP port 1900 (SSDP) free on the machine and the phone on the same network. Selecting the device in YouTube shows the
`POST /apps/YouTube` body (`pairingCode=...&theme=cl&dialLaunch=watch|browse`) and the `register_pairing_code` result.
Playback will not start: there is no lounge client behind the probe. Pairing codes are short-lived but treat logs as private.
