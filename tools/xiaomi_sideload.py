#!/usr/bin/env python3
"""Pure Python Xiaomi MIAssistant sideload implementation.

Replaces the buggy MiAssistantTool C binary with a clean Python
implementation using pyusb. Handles the full flow:
  1. USB device discovery and ADB protocol handshake
  2. Device info query
  3. ROM validation via Xiaomi server
  4. Sideload transfer with progress

Usage:
    python3 xiaomi_sideload.py flash <rom.zip>
    python3 xiaomi_sideload.py info
    python3 xiaomi_sideload.py validate <rom.zip>
    python3 xiaomi_sideload.py format-data
    python3 xiaomi_sideload.py reboot
"""

import base64
import hashlib
import json
import os
import struct
import sys
import urllib.parse
import urllib.request

import usb.core
import usb.util
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# ADB protocol constants
ADB_CLASS = 0xFF
ADB_SUB_CLASS = 0x42
ADB_PROTOCOL = 1
ADB_CONNECT = 0x4E584E43
ADB_VERSION = 0x01000001
ADB_OPEN = 0x4E45504F
ADB_OKAY = 0x59414B4F
ADB_WRTE = 0x45545257
ADB_CLSE = 0x45534C43
ADB_MAX_DATA = 1024 * 1024
SIDELOAD_CHUNK_SIZE = 64 * 1024

# Xiaomi validation AES key/iv
KEY = bytes([0x6D, 0x69, 0x75, 0x69, 0x6F, 0x74, 0x61, 0x76, 0x61, 0x6C, 0x69, 0x64, 0x65, 0x64, 0x31, 0x31])
IV = bytes([0x30, 0x31, 0x30, 0x32, 0x30, 0x33, 0x30, 0x34, 0x30, 0x35, 0x30, 0x36, 0x30, 0x37, 0x30, 0x38])

VALIDATE_URL = "http://update.miui.com/updates/miotaV3.php"


class XiaomiSideload:
    def __init__(self):
        self.dev = None
        self.ep_in = None
        self.ep_out = None
        self.intf_num = None
        self.device_info = {}

    def find_device(self):
        """Find a Xiaomi device in MIAssistant sideload mode."""
        # Look for Google/Xiaomi ADB vendor IDs specifically
        for vid in (0x18D1, 0x2717):
            dev = usb.core.find(idVendor=vid)
            if dev is None:
                continue
            try:
                cfg = dev.get_active_configuration()
            except Exception:  # noqa: S112 — skip non-configurable USB devices
                continue
            for intf in cfg:
                if (
                    intf.bInterfaceClass == ADB_CLASS
                    and intf.bInterfaceSubClass == ADB_SUB_CLASS
                    and intf.bInterfaceProtocol == ADB_PROTOCOL
                ):
                    ep_in = ep_out = None
                    for ep in intf:
                        if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                            ep_in = ep
                        else:
                            ep_out = ep
                    if ep_in and ep_out:
                        self.dev = dev
                        self.ep_in = ep_in
                        self.ep_out = ep_out
                        self.intf_num = intf.bInterfaceNumber
                        return True
        return False

    def connect(self):
        """Find device and establish ADB connection."""
        if not self.find_device():
            print("ERROR: No device in MIAssistant sideload mode.")
            return False

        # Detach kernel driver if needed
        try:
            if self.dev.is_kernel_driver_active(self.intf_num):
                self.dev.detach_kernel_driver(self.intf_num)
        except Exception:
            pass

        usb.util.claim_interface(self.dev, self.intf_num)

        # ADB CONNECT handshake
        self._send_cmd(ADB_CONNECT, ADB_VERSION, ADB_MAX_DATA, b"host::\x00")
        pkt, data = self._recv_pkt()
        if not data.startswith(b"sideload::"):
            print(f"ERROR: Unexpected response: {data[:50]}")
            return False

        return True

    def _send_cmd(self, cmd, arg0, arg1, data=b""):
        """Send an ADB command packet."""
        header = struct.pack("<IIIIII", cmd, arg0, arg1, len(data), 0, cmd ^ 0xFFFFFFFF)
        self.ep_out.write(header, timeout=5000)
        if data:
            self.ep_out.write(data, timeout=5000)

    def _recv_pkt(self):
        """Receive an ADB packet, return (header_tuple, data_bytes)."""
        raw = bytes(self.ep_in.read(24, timeout=10000))
        if len(raw) < 24:
            return None, b""
        cmd, arg0, arg1, length, checksum, magic = struct.unpack("<IIIIII", raw)
        data = b""
        if length > 0:
            data = bytes(self.ep_in.read(length, timeout=10000))
        return (cmd, arg0, arg1, length), data

    def adb_cmd(self, command):
        """Send an ADB command and return the response string."""
        cmd_bytes = command.encode() if isinstance(command, str) else command
        self._send_cmd(ADB_OPEN, 1, 0, cmd_bytes)

        # Read OKAY
        pkt, data = self._recv_pkt()
        # Read response
        pkt, data = self._recv_pkt()
        # Read CLSE
        self._recv_pkt()

        result = data.decode("utf-8", errors="replace").strip()
        return result

    def read_info(self):
        """Read device info from MIAssistant."""
        self.device_info = {
            "Device": self.adb_cmd("getdevice:"),
            "Version": self.adb_cmd("getversion:"),
            "Serial Number": self.adb_cmd("getsn:"),
            "Codebase": self.adb_cmd("getcodebase:"),
            "Branch": self.adb_cmd("getbranch:"),
            "Language": self.adb_cmd("getlanguage:"),
            "Region": self.adb_cmd("getregion:"),
            "ROM Zone": self.adb_cmd("getromzone:"),
        }
        return self.device_info

    def validate_rom(self, md5):
        """Call Xiaomi's validation server and return the validation token."""
        info = self.device_info
        req_json = json.dumps(
            {
                "d": info.get("Device", ""),
                "v": info.get("Version", ""),
                "c": info.get("Codebase", ""),
                "b": info.get("Branch", ""),
                "sn": info.get("Serial Number", ""),
                "l": "en-US",
                "f": "1",
                "options": {"zone": int(info.get("ROM Zone", "2"))},
                "pkg": md5,
            },
            separators=(",", ":"),
        )

        # Encrypt
        pad_len = 16 - (len(req_json) % 16)
        padded = req_json.encode() + bytes([pad_len] * pad_len)
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
        enc = cipher.encryptor()
        encrypted = enc.update(padded) + enc.finalize()
        encoded = base64.b64encode(encrypted).decode()
        url_encoded = urllib.parse.quote(encoded, safe="")

        post_data = f"q={url_encoded}&t=&s=1".encode()
        req = urllib.request.Request(  # noqa: S310 — Xiaomi validation endpoint
            VALIDATE_URL,
            data=post_data,
            headers={"User-Agent": "MiTunes_UserAgent_v3.0"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            response_data = resp.read()

        # Decrypt response
        decoded = base64.b64decode(response_data)
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
        dec = cipher.decryptor()
        decrypted = dec.update(decoded) + dec.finalize()
        # Remove PKCS7 padding
        pad = decrypted[-1]
        if 1 <= pad <= 16:
            decrypted = decrypted[:-pad]

        text = decrypted.decode("utf-8", errors="replace")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0:
            return None, "No JSON in response"

        data = json.loads(text[start:end])

        if "PkgRom" in data:
            pkg = data["PkgRom"]
            erase = int(pkg.get("Erase", "0"))
            validate = pkg.get("Validate", "")
            return validate, f"erase={erase}"
        elif "Code" in data:
            msg = data.get("Code", {}).get("message", "Unknown error")
            return None, msg
        else:
            return None, f"Unexpected: {text[start:end][:200]}"

    def sideload(self, filepath, validate_token, progress_cb=None):
        """Transfer a ROM file to the device using the MIAssistant sideload protocol."""
        file_size = os.path.getsize(filepath)
        cmd_str = f"sideload-host:{file_size}:{SIDELOAD_CHUNK_SIZE}:{validate_token}:0"

        self._send_cmd(ADB_OPEN, 1, 0, cmd_str.encode() + b"\x00")

        total_sent = 0
        last_pct = -1

        with open(filepath, "rb") as fp:
            while True:
                try:
                    pkt, data = self._recv_pkt()
                except Exception:
                    if total_sent > 0:
                        print(f"\nTransfer interrupted at {total_sent}/{file_size} bytes")
                    break

                if pkt is None:
                    break

                cmd, arg0, arg1, length = pkt

                # Check for completion message (data > 8 bytes = status message)
                if len(data) > 8:
                    msg = data.decode("utf-8", errors="replace").strip()
                    print(f"\nDevice response: {msg}")
                    break

                if cmd == ADB_OKAY:
                    self._send_cmd(ADB_OKAY, arg1, arg0)
                    continue

                if cmd != ADB_WRTE:
                    continue

                # Parse block number from data
                block_str = data.decode("utf-8", errors="replace").strip()
                try:
                    block = int(block_str)
                except ValueError:
                    continue

                offset = block * SIDELOAD_CHUNK_SIZE
                if offset > file_size:
                    break

                to_read = min(SIDELOAD_CHUNK_SIZE, file_size - offset)
                fp.seek(offset)
                chunk = fp.read(to_read)

                self._send_cmd(ADB_WRTE, arg1, arg0, chunk)
                self._send_cmd(ADB_OKAY, arg1, arg0)
                total_sent += to_read

                pct = int(total_sent * 100 / file_size)
                if pct != last_pct:
                    last_pct = pct
                    if progress_cb:
                        progress_cb(pct, total_sent, file_size)
                    else:
                        print(
                            f"\rFlashing: {pct}% ({total_sent // (1024 * 1024)} / {file_size // (1024 * 1024)} MB)",
                            end="",
                            flush=True,
                        )

        print(f"\nTransfer complete: {total_sent // (1024 * 1024)} MB sent")
        return total_sent > 0

    def format_data(self):
        """Format data partition."""
        result = self.adb_cmd("format-data:")
        print(f"Format: {result}")
        return result

    def reboot(self):
        """Reboot device."""
        result = self.adb_cmd("reboot:")
        print(f"Reboot: {result}")
        return result

    def close(self):
        """Release USB interface."""
        if self.dev and self.intf_num is not None:
            try:
                usb.util.release_interface(self.dev, self.intf_num)
            except Exception:
                pass


def compute_md5(filepath):
    """Compute MD5 of a file with progress."""
    size = os.path.getsize(filepath)
    md5 = hashlib.md5()  # noqa: S324 — required by Xiaomi MIAssistant protocol
    done = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            md5.update(chunk)
            done += len(chunk)
            pct = done * 100 // size
            print(f"\rComputing MD5: {pct}%", end="", flush=True)
    print()
    return md5.hexdigest()


def main():
    if len(sys.argv) < 2:
        print("Usage: xiaomi_sideload.py <command> [args]")
        print("  info              - Read device info")
        print("  validate <rom>    - Validate ROM with Xiaomi server")
        print("  flash <rom>       - Full flash: validate + sideload")
        print("  format-data       - Format data partition")
        print("  reboot            - Reboot device")
        sys.exit(1)

    cmd = sys.argv[1]
    xs = XiaomiSideload()

    print("Connecting to device...")
    if not xs.connect():
        sys.exit(1)
    print("Connected!")

    try:
        info = xs.read_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        print()

        if cmd == "info":
            pass

        elif cmd == "validate":
            filepath = sys.argv[2]
            print("Computing MD5...")
            md5 = compute_md5(filepath)
            print(f"MD5: {md5}")
            print("Validating with Xiaomi server...")
            token, msg = xs.validate_rom(md5)
            if token:
                print(f"Validation OK ({msg})")
                print(f"Token: {token[:50]}...")
            else:
                print(f"REJECTED: {msg}")
                sys.exit(1)

        elif cmd == "flash":
            filepath = sys.argv[2]
            if not os.path.isfile(filepath):
                print(f"File not found: {filepath}")
                sys.exit(1)

            print("Computing MD5...")
            md5 = compute_md5(filepath)
            print(f"MD5: {md5}")

            print("Validating with Xiaomi server...")
            token, msg = xs.validate_rom(md5)
            if not token:
                print(f"REJECTED: {msg}")
                sys.exit(1)
            print(f"Validation OK ({msg})")
            print()

            print("Starting sideload transfer...")
            print("Do NOT unplug the USB cable!")
            print()
            success = xs.sideload(filepath, token)
            if success:
                print("\nFlash complete! Device should install and reboot.")
            else:
                print("\nFlash may have failed.")
                sys.exit(1)

        elif cmd == "format-data":
            xs.format_data()

        elif cmd == "reboot":
            xs.reboot()

        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)

    finally:
        xs.close()


if __name__ == "__main__":
    main()
