"""
Ninebot / Xiaomi electric scooter serial protocol and BLE communication layer.

Supports:
- Ninebot protocol (0x5AA5 header) with XModem CRC16
- Xiaomi M365 protocol (0x55AA header) with additive checksum
- BLE transport via bleak (async)
- DFU (Device Firmware Update) state machine
- Scooter info reading (serial, firmware versions, UID)

Typical usage (from a Flask route running in a thread with asyncio.run()):

    info = asyncio.run(read_scooter_info("AA:BB:CC:DD:EE:FF"))
    asyncio.run(flash_firmware("AA:BB:CC:DD:EE:FF", "/path/fw.zip", cb))

bleak is an optional dependency. A clear ImportError is raised on first use if
the package is not installed.
"""

from __future__ import annotations

import asyncio
import io
import struct
import zipfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Sequence

# ---------------------------------------------------------------------------
# Optional bleak import — fail loudly with an actionable message on first use
# ---------------------------------------------------------------------------

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic

    _BLEAK_AVAILABLE = True
except ImportError:
    _BLEAK_AVAILABLE = False

    # Stub so the module-level type annotations resolve
    class BleakClient:  # type: ignore[no-redef]
        pass

    class BleakGATTCharacteristic:  # type: ignore[no-redef]
        pass


def _require_bleak() -> None:
    """Raise a clear error when bleak is not installed."""
    if not _BLEAK_AVAILABLE:
        raise ImportError(
            "The 'bleak' package is required for BLE scooter communication.\n"
            "Install it with:  pip install bleak\n"
            "Then restart the Osmosis server."
        )


# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

# Ninebot
NB_MAGIC_0 = 0x5A
NB_MAGIC_1 = 0xA5

# Xiaomi M365
MI_MAGIC_0 = 0x55
MI_MAGIC_1 = 0xAA

# Source / destination addresses
ADDR_APP = 0x20   # BLE app / host
ADDR_ESC = 0x21   # Electric Speed Controller (main board)
ADDR_BMS = 0x22   # Battery Management System
ADDR_EXT_BMS = 0x23  # External / secondary BMS

# Commands
CMD_READ_REG = 0x01   # Read register / get version
CMD_WRITE_REG = 0x02  # Write register
CMD_READ_INFO = 0x10  # Read device info block
CMD_DFU_START = 0x07  # Initiate DFU session
CMD_DFU_DATA = 0x08   # Send firmware chunk
CMD_DFU_VERIFY = 0x09  # Verify / finalize DFU

# BLE UUIDs — Ninebot custom service
NB_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
NB_WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
NB_NOTIFY_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# BLE UUIDs — Xiaomi M365 / Nordic UART Service
MI_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
MI_WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
MI_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Alternative Xiaomi service (older M365 firmware)
MI_ALT_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"

# DFU chunk size in bytes
DFU_CHUNK_SIZE = 128

# BLE operation timeout (seconds)
BLE_TIMEOUT = 10.0

# How long to wait for a BLE notification reply (seconds)
REPLY_TIMEOUT = 5.0

# Maximum number of retries for a single BLE write
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# DFU state machine
# ---------------------------------------------------------------------------


class DFUState(Enum):
    IDLE = auto()
    VER_INIT = auto()    # Negotiate protocol / firmware version with device
    SEND_FW = auto()     # Streaming firmware chunks
    WR_INFO = auto()     # Writing firmware metadata
    DFU_VERIFY = auto()  # Requesting CRC/hash verification on device
    DFU_ACTIVE = auto()  # Device is applying the new firmware
    VER_DONE = auto()    # Verification confirmed by device
    DONE = auto()        # Session complete
    ERROR = auto()       # Unrecoverable failure


# ---------------------------------------------------------------------------
# CRC / checksum helpers
# ---------------------------------------------------------------------------


def _crc16_xmodem(data: bytes | bytearray) -> int:
    """XModem CRC16 — used by the Ninebot protocol."""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def _xiaomi_checksum(data: bytes | bytearray) -> int:
    """Additive checksum used by the Xiaomi M365 protocol.

    Sum all bytes then XOR with 0xFFFF, keeping only the lower 16 bits.
    """
    return (sum(data) ^ 0xFFFF) & 0xFFFF


# ---------------------------------------------------------------------------
# Ninebot packet
# ---------------------------------------------------------------------------


class NinebotPacket:
    """Build and parse Ninebot 0x5AA5 protocol packets.

    Wire format:
        [0x5A, 0xA5, bLen, bSrcAddr, bDstAddr, bCmd, bArg, *payload,
         crcLow, crcHigh]

    bLen = len(payload) + 2  (covers bCmd and bArg)
    CRC covers bytes from bLen up to and including the last payload byte.
    """

    def __init__(
        self,
        src: int,
        dst: int,
        cmd: int,
        arg: int,
        payload: bytes | bytearray = b"",
    ) -> None:
        self.src = src
        self.dst = dst
        self.cmd = cmd
        self.arg = arg
        self.payload = bytes(payload)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def encode(self) -> bytes:
        """Serialise the packet to bytes ready for transmission."""
        b_len = len(self.payload) + 2  # +2 for cmd and arg
        crc_data = bytes([b_len, self.src, self.dst, self.cmd, self.arg]) + self.payload
        crc = _crc16_xmodem(crc_data)
        return bytes(
            [
                NB_MAGIC_0,
                NB_MAGIC_1,
                b_len,
                self.src,
                self.dst,
                self.cmd,
                self.arg,
            ]
        ) + self.payload + struct.pack("<H", crc)

    # ------------------------------------------------------------------
    # Deserialisation
    # ------------------------------------------------------------------

    @classmethod
    def decode(cls, data: bytes | bytearray) -> "NinebotPacket":
        """Parse raw bytes into a NinebotPacket.

        Raises:
            ValueError: if the header magic, length, or CRC is invalid.
        """
        data = bytes(data)
        if len(data) < 9:
            raise ValueError(f"Ninebot packet too short: {len(data)} bytes")
        if data[0] != NB_MAGIC_0 or data[1] != NB_MAGIC_1:
            raise ValueError(f"Bad Ninebot magic: 0x{data[0]:02X}{data[1]:02X}")

        b_len = data[2]
        # b_len = payload + 2; total expected = 7 (header) + b_len - 2 + 2 (crc)
        expected_total = 7 + b_len  # 5 header bytes before payload + b_len + 2 crc
        # Simpler: after magic (2), we have bLen(1)+src(1)+dst(1)+cmd(1)+arg(1) = 5 bytes
        # then (b_len - 2) payload bytes, then 2 CRC bytes
        payload_len = b_len - 2
        if payload_len < 0:
            raise ValueError(f"Ninebot bLen={b_len} is too small (min 2)")
        expected_total = 2 + 1 + 4 + payload_len + 2  # magic+bLen+src,dst,cmd,arg+payload+crc
        if len(data) < expected_total:
            raise ValueError(
                f"Ninebot packet incomplete: need {expected_total} bytes, got {len(data)}"
            )

        src = data[3]
        dst = data[4]
        cmd = data[5]
        arg = data[6]
        payload = data[7 : 7 + payload_len]

        # Verify CRC (covers from bLen to end of payload)
        crc_input = data[2 : 7 + payload_len]
        expected_crc = _crc16_xmodem(crc_input)
        received_crc = struct.unpack_from("<H", data, 7 + payload_len)[0]
        if received_crc != expected_crc:
            raise ValueError(
                f"Ninebot CRC mismatch: expected 0x{expected_crc:04X}, "
                f"got 0x{received_crc:04X}"
            )

        return cls(src=src, dst=dst, cmd=cmd, arg=arg, payload=payload)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"NinebotPacket(src=0x{self.src:02X}, dst=0x{self.dst:02X}, "
            f"cmd=0x{self.cmd:02X}, arg=0x{self.arg:02X}, "
            f"payload={self.payload.hex()})"
        )

    @staticmethod
    def read_register(register: int, length: int = 1) -> "NinebotPacket":
        """Build a read-register request packet (app -> ESC)."""
        return NinebotPacket(
            src=ADDR_APP,
            dst=ADDR_ESC,
            cmd=CMD_READ_INFO,
            arg=length,
            payload=struct.pack("<H", register),
        )

    @staticmethod
    def get_version() -> "NinebotPacket":
        """Build a get-version request packet."""
        return NinebotPacket(
            src=ADDR_APP,
            dst=ADDR_ESC,
            cmd=CMD_READ_REG,
            arg=0x00,
            payload=b"",
        )


# ---------------------------------------------------------------------------
# Xiaomi packet
# ---------------------------------------------------------------------------


class XiaomiPacket:
    """Build and parse Xiaomi 0x55AA protocol packets.

    Wire format:
        [0x55, 0xAA, bLen, bSrcAddr, bDstAddr, bCmd, bArg, *payload,
         checksumLow, checksumHigh]

    bLen = len(payload) + 2
    Checksum = (sum(bLen..last_payload_byte) XOR 0xFFFF) & 0xFFFF
    """

    def __init__(
        self,
        src: int,
        dst: int,
        cmd: int,
        arg: int,
        payload: bytes | bytearray = b"",
    ) -> None:
        self.src = src
        self.dst = dst
        self.cmd = cmd
        self.arg = arg
        self.payload = bytes(payload)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def encode(self) -> bytes:
        """Serialise the packet to bytes."""
        b_len = len(self.payload) + 2
        checksum_data = bytes([b_len, self.src, self.dst, self.cmd, self.arg]) + self.payload
        checksum = _xiaomi_checksum(checksum_data)
        return bytes(
            [
                MI_MAGIC_0,
                MI_MAGIC_1,
                b_len,
                self.src,
                self.dst,
                self.cmd,
                self.arg,
            ]
        ) + self.payload + struct.pack("<H", checksum)

    # ------------------------------------------------------------------
    # Deserialisation
    # ------------------------------------------------------------------

    @classmethod
    def decode(cls, data: bytes | bytearray) -> "XiaomiPacket":
        """Parse raw bytes into a XiaomiPacket.

        Raises:
            ValueError: if magic, length, or checksum is invalid.
        """
        data = bytes(data)
        if len(data) < 9:
            raise ValueError(f"Xiaomi packet too short: {len(data)} bytes")
        if data[0] != MI_MAGIC_0 or data[1] != MI_MAGIC_1:
            raise ValueError(f"Bad Xiaomi magic: 0x{data[0]:02X}{data[1]:02X}")

        b_len = data[2]
        payload_len = b_len - 2
        if payload_len < 0:
            raise ValueError(f"Xiaomi bLen={b_len} is too small (min 2)")
        expected_total = 2 + 1 + 4 + payload_len + 2
        if len(data) < expected_total:
            raise ValueError(
                f"Xiaomi packet incomplete: need {expected_total} bytes, got {len(data)}"
            )

        src = data[3]
        dst = data[4]
        cmd = data[5]
        arg = data[6]
        payload = data[7 : 7 + payload_len]

        checksum_input = data[2 : 7 + payload_len]
        expected_checksum = _xiaomi_checksum(checksum_input)
        received_checksum = struct.unpack_from("<H", data, 7 + payload_len)[0]
        if received_checksum != expected_checksum:
            raise ValueError(
                f"Xiaomi checksum mismatch: expected 0x{expected_checksum:04X}, "
                f"got 0x{received_checksum:04X}"
            )

        return cls(src=src, dst=dst, cmd=cmd, arg=arg, payload=payload)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"XiaomiPacket(src=0x{self.src:02X}, dst=0x{self.dst:02X}, "
            f"cmd=0x{self.cmd:02X}, arg=0x{self.arg:02X}, "
            f"payload={self.payload.hex()})"
        )

    @staticmethod
    def read_register(register: int, length: int = 1) -> "XiaomiPacket":
        """Build a read-register request packet."""
        return XiaomiPacket(
            src=ADDR_APP,
            dst=ADDR_ESC,
            cmd=CMD_READ_INFO,
            arg=length,
            payload=struct.pack("<H", register),
        )

    @staticmethod
    def get_version() -> "XiaomiPacket":
        """Build a get-version request packet."""
        return XiaomiPacket(
            src=ADDR_APP,
            dst=ADDR_ESC,
            cmd=CMD_READ_REG,
            arg=0x00,
            payload=b"",
        )


# ---------------------------------------------------------------------------
# Scooter info dataclass
# ---------------------------------------------------------------------------


@dataclass
class ScooterInfo:
    """Structured information read from a scooter over BLE."""

    address: str = ""
    serial: str = ""
    model: str = ""
    uid: str = ""

    # Firmware version strings
    fw_drv: str = ""    # Main drive / ESC firmware
    fw_ble: str = ""    # BLE module firmware
    fw_bms: str = ""    # Battery Management System firmware
    fw_mcu: str = ""    # Microcontroller Unit firmware
    fw_vcu: str = ""    # Vehicle Control Unit firmware

    # Raw register values captured during info read
    _raw: dict = field(default_factory=dict, repr=False)

    def as_dict(self) -> dict:
        """Return a JSON-serialisable dict (omits private _raw field)."""
        return {
            "address": self.address,
            "serial": self.serial,
            "model": self.model,
            "uid": self.uid,
            "fw_drv": self.fw_drv,
            "fw_ble": self.fw_ble,
            "fw_bms": self.fw_bms,
            "fw_mcu": self.fw_mcu,
            "fw_vcu": self.fw_vcu,
        }


# ---------------------------------------------------------------------------
# Protocol variant detection
# ---------------------------------------------------------------------------


class _Protocol(Enum):
    NINEBOT = "ninebot"
    XIAOMI = "xiaomi"


def _detect_protocol(service_uuids: Sequence[str]) -> _Protocol:
    """Infer the protocol from the BLE service UUIDs advertised by the device."""
    lowered = [u.lower() for u in service_uuids]
    for uuid in lowered:
        if MI_SERVICE_UUID.lower() in uuid or MI_ALT_SERVICE_UUID.lower() in uuid:
            return _Protocol.XIAOMI
        if NB_SERVICE_UUID.lower() in uuid:
            return _Protocol.NINEBOT
    # Default to Ninebot when ambiguous — covers most modern Segway/Ninebot scooters
    return _Protocol.NINEBOT


# ---------------------------------------------------------------------------
# ScooterBLE — async BLE transport wrapper
# ---------------------------------------------------------------------------


class ScooterBLE:
    """Async BLE client for Ninebot / Xiaomi scooters.

    Wraps bleak to provide a higher-level connect/disconnect/request API with
    proper timeout handling and notification-based reply matching.

    Usage::

        async with ScooterBLE("AA:BB:CC:DD:EE:FF") as ble:
            reply = await ble.request(NinebotPacket.get_version())
    """

    def __init__(self, address: str, timeout: float = BLE_TIMEOUT) -> None:
        _require_bleak()
        self.address = address
        self.timeout = timeout
        self._client: BleakClient | None = None
        self._protocol: _Protocol = _Protocol.NINEBOT
        self._write_uuid: str = NB_WRITE_UUID
        self._notify_uuid: str = NB_NOTIFY_UUID
        self._reply_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._rx_buf: bytearray = bytearray()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "ScooterBLE":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the scooter and subscribe to notifications.

        Raises:
            RuntimeError: if connection or service discovery fails.
        """
        _require_bleak()
        self._client = BleakClient(self.address, timeout=self.timeout)
        try:
            await self._client.connect()
        except Exception as exc:
            raise RuntimeError(f"BLE connect failed for {self.address}: {exc}") from exc

        if not self._client.is_connected:
            raise RuntimeError(f"BLE device {self.address} not connected after attempt")

        # Detect protocol from advertised services
        service_uuids = [str(s.uuid) for s in self._client.services]
        self._protocol = _detect_protocol(service_uuids)

        if self._protocol == _Protocol.XIAOMI:
            self._write_uuid = MI_WRITE_UUID
            self._notify_uuid = MI_NOTIFY_UUID
        else:
            self._write_uuid = NB_WRITE_UUID
            self._notify_uuid = NB_NOTIFY_UUID

        # Subscribe to notifications
        try:
            await self._client.start_notify(self._notify_uuid, self._on_notify)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to subscribe to BLE notifications on {self._notify_uuid}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Gracefully disconnect from the scooter."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(self._notify_uuid)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None

    # ------------------------------------------------------------------
    # BLE notification handler
    # ------------------------------------------------------------------

    def _on_notify(self, _characteristic: BleakGATTCharacteristic, data: bytearray) -> None:
        """Accumulate incoming BLE notification chunks into the RX buffer.

        Ninebot and Xiaomi packets can be split across multiple BLE MTU
        frames.  We buffer until we have a complete, valid packet then push
        it onto the reply queue.
        """
        self._rx_buf.extend(data)

        # Try to extract a complete packet from the buffer
        while len(self._rx_buf) >= 9:
            magic0 = self._rx_buf[0]
            magic1 = self._rx_buf[1]

            if magic0 == NB_MAGIC_0 and magic1 == NB_MAGIC_1:
                b_len = self._rx_buf[2]
                payload_len = max(b_len - 2, 0)
                total = 2 + 1 + 4 + payload_len + 2  # magic+bLen+4hdr+payload+crc
                if len(self._rx_buf) < total:
                    break  # wait for more data
                pkt_bytes = bytes(self._rx_buf[:total])
                del self._rx_buf[:total]
                self._reply_queue.put_nowait(pkt_bytes)

            elif magic0 == MI_MAGIC_0 and magic1 == MI_MAGIC_1:
                b_len = self._rx_buf[2]
                payload_len = max(b_len - 2, 0)
                total = 2 + 1 + 4 + payload_len + 2
                if len(self._rx_buf) < total:
                    break
                pkt_bytes = bytes(self._rx_buf[:total])
                del self._rx_buf[:total]
                self._reply_queue.put_nowait(pkt_bytes)

            else:
                # Out-of-sync: discard one byte and try again
                del self._rx_buf[0]

    # ------------------------------------------------------------------
    # Low-level write
    # ------------------------------------------------------------------

    async def _write(self, data: bytes) -> None:
        """Write raw bytes to the BLE write characteristic."""
        if not self._client or not self._client.is_connected:
            raise RuntimeError("BLE client is not connected")
        try:
            await self._client.write_gatt_char(self._write_uuid, data, response=False)
        except Exception as exc:
            raise RuntimeError(f"BLE write failed: {exc}") from exc

    # ------------------------------------------------------------------
    # High-level request/response
    # ------------------------------------------------------------------

    async def request(
        self,
        packet: NinebotPacket | XiaomiPacket,
        timeout: float = REPLY_TIMEOUT,
    ) -> NinebotPacket | XiaomiPacket:
        """Send a packet and wait for the reply notification.

        Automatically retries up to MAX_RETRIES times on timeout.

        Returns:
            The parsed reply packet.

        Raises:
            RuntimeError: if no reply is received within the timeout after all retries.
            ValueError: if the reply packet fails checksum/CRC validation.
        """
        raw = packet.encode()
        last_exc: Exception = RuntimeError("No attempts made")

        for attempt in range(1, MAX_RETRIES + 1):
            # Drain stale notifications before sending
            while not self._reply_queue.empty():
                self._reply_queue.get_nowait()

            await self._write(raw)

            try:
                reply_bytes = await asyncio.wait_for(
                    self._reply_queue.get(), timeout=timeout
                )
                # Parse and validate
                if self._protocol == _Protocol.XIAOMI:
                    return XiaomiPacket.decode(reply_bytes)
                return NinebotPacket.decode(reply_bytes)

            except asyncio.TimeoutError as exc:
                last_exc = RuntimeError(
                    f"BLE reply timeout (attempt {attempt}/{MAX_RETRIES}) "
                    f"for cmd=0x{packet.cmd:02X}"
                )
            except ValueError as exc:
                last_exc = exc

        raise last_exc

    async def write_no_reply(self, packet: NinebotPacket | XiaomiPacket) -> None:
        """Fire-and-forget write (e.g. for streaming DFU data chunks)."""
        await self._write(packet.encode())

    @property
    def protocol(self) -> _Protocol:
        return self._protocol


# ---------------------------------------------------------------------------
# Scooter info reading
# ---------------------------------------------------------------------------

# Register addresses (Ninebot / Xiaomi shared register map)
_REG_SERIAL = 0x10
_REG_MODEL = 0x17
_REG_UID = 0x1A
_REG_FW_DRV = 0x1B
_REG_FW_BLE = 0x1C
_REG_FW_BMS = 0x1D
_REG_FW_MCU = 0x20
_REG_FW_VCU = 0x21


def _decode_version(raw: bytes) -> str:
    """Decode a 2-byte little-endian version word to a 'major.minor' string."""
    if len(raw) < 2:
        return ""
    word = struct.unpack_from("<H", raw)[0]
    return f"{word >> 8}.{word & 0xFF}"


def _decode_string(raw: bytes) -> str:
    """Decode a null-terminated ASCII/UTF-8 string from register payload."""
    try:
        null = raw.index(0)
        raw = raw[:null]
    except ValueError:
        pass
    return raw.decode("ascii", errors="replace").strip()


async def _read_register(
    ble: ScooterBLE,
    register: int,
    length: int = 2,
) -> bytes:
    """Send a read-register request and return the reply payload.

    Returns an empty bytes object if the read fails rather than raising,
    so that partial info can still be returned to the caller.
    """
    try:
        if ble.protocol == _Protocol.XIAOMI:
            pkt = XiaomiPacket.read_register(register, length)
        else:
            pkt = NinebotPacket.read_register(register, length)
        reply = await ble.request(pkt)
        return reply.payload
    except Exception:
        return b""


async def read_scooter_info(address: str) -> ScooterInfo:
    """Connect to a scooter and read its identifying information.

    Args:
        address: BLE MAC address (or UUID on macOS) of the scooter.

    Returns:
        Populated ScooterInfo dataclass.

    Raises:
        RuntimeError: if BLE connection fails.
        ImportError: if bleak is not installed.
    """
    _require_bleak()
    info = ScooterInfo(address=address)

    async with ScooterBLE(address) as ble:
        raw_serial = await _read_register(ble, _REG_SERIAL, 14)
        info.serial = _decode_string(raw_serial)
        info._raw["serial"] = raw_serial.hex()

        raw_model = await _read_register(ble, _REG_MODEL, 4)
        info.model = _decode_string(raw_model)
        info._raw["model"] = raw_model.hex()

        raw_uid = await _read_register(ble, _REG_UID, 6)
        info.uid = raw_uid.hex().upper()
        info._raw["uid"] = raw_uid.hex()

        raw_drv = await _read_register(ble, _REG_FW_DRV, 2)
        info.fw_drv = _decode_version(raw_drv)

        raw_ble = await _read_register(ble, _REG_FW_BLE, 2)
        info.fw_ble = _decode_version(raw_ble)

        raw_bms = await _read_register(ble, _REG_FW_BMS, 2)
        info.fw_bms = _decode_version(raw_bms)

        raw_mcu = await _read_register(ble, _REG_FW_MCU, 2)
        info.fw_mcu = _decode_version(raw_mcu)

        raw_vcu = await _read_register(ble, _REG_FW_VCU, 2)
        info.fw_vcu = _decode_version(raw_vcu)

    return info


# ---------------------------------------------------------------------------
# DFU — Device Firmware Update
# ---------------------------------------------------------------------------


class DFUError(Exception):
    """Raised when the DFU process encounters an unrecoverable error."""


def _load_firmware(fw_path: str | Path) -> bytes:
    """Load raw firmware bytes from a file.

    Accepts:
    - .zip containing a single .bin/.hex file (Xiaomi/Ninebot OTA format)
    - Raw .bin / .hex file
    """
    path = Path(fw_path)
    if not path.exists():
        raise FileNotFoundError(f"Firmware file not found: {path}")

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            # Find the firmware binary inside the zip
            candidates = [
                n for n in zf.namelist()
                if n.lower().endswith((".bin", ".hex")) and not n.startswith("__MACOSX")
            ]
            if not candidates:
                raise DFUError(
                    f"No .bin or .hex firmware found inside {path.name}. "
                    f"ZIP contents: {zf.namelist()}"
                )
            # Prefer files at the root of the archive
            candidates.sort(key=lambda n: n.count("/"))
            fw_name = candidates[0]
            return zf.read(fw_name)

    return path.read_bytes()


class _DFUSession:
    """Internal DFU session that drives the state machine over BLE.

    This is intentionally separated from the public flash_firmware() function
    so that it can be unit-tested without BLE hardware.
    """

    def __init__(
        self,
        ble: ScooterBLE,
        fw_data: bytes,
        on_progress: Callable[[int, int, DFUState], None] | None,
    ) -> None:
        self._ble = ble
        self._fw = fw_data
        self._on_progress = on_progress
        self.state: DFUState = DFUState.IDLE

    def _emit(self, sent: int, total: int) -> None:
        if self._on_progress:
            try:
                self._on_progress(sent, total, self.state)
            except Exception:
                pass

    def _make_packet(
        self, cmd: int, arg: int, payload: bytes = b""
    ) -> NinebotPacket | XiaomiPacket:
        if self._ble.protocol == _Protocol.XIAOMI:
            return XiaomiPacket(src=ADDR_APP, dst=ADDR_ESC, cmd=cmd, arg=arg, payload=payload)
        return NinebotPacket(src=ADDR_APP, dst=ADDR_ESC, cmd=cmd, arg=arg, payload=payload)

    async def run(self) -> None:
        """Execute the full DFU state machine.

        State transitions:
            IDLE -> VER_INIT -> SEND_FW -> WR_INFO -> DFU_VERIFY
                 -> DFU_ACTIVE -> VER_DONE -> DONE
        """
        fw = self._fw
        total = len(fw)

        # ------------------------------------------------------------------
        # VER_INIT: negotiate version / announce DFU intent
        # ------------------------------------------------------------------
        self.state = DFUState.VER_INIT
        self._emit(0, total)

        ver_payload = struct.pack("<I", total)  # advertise firmware size
        init_pkt = self._make_packet(CMD_DFU_START, 0x00, ver_payload)
        try:
            reply = await self._ble.request(init_pkt, timeout=REPLY_TIMEOUT)
        except Exception as exc:
            self.state = DFUState.ERROR
            raise DFUError(f"DFU init handshake failed: {exc}") from exc

        # Device should ACK with arg == 0x01
        if reply.arg != 0x01:
            self.state = DFUState.ERROR
            raise DFUError(
                f"DFU init rejected by device (arg=0x{reply.arg:02X}); "
                "check firmware compatibility"
            )

        # ------------------------------------------------------------------
        # SEND_FW: stream firmware in fixed-size chunks
        # ------------------------------------------------------------------
        self.state = DFUState.SEND_FW
        self._emit(0, total)

        offset = 0
        chunk_index = 0

        while offset < total:
            chunk = fw[offset : offset + DFU_CHUNK_SIZE]
            # Payload: [chunk_index u16 LE] + chunk bytes
            payload = struct.pack("<H", chunk_index) + chunk
            data_pkt = self._make_packet(CMD_DFU_DATA, 0x00, payload)

            # For data chunks we use write-with-reply for every 16th chunk
            # (device ACKs progress) and fire-and-forget for the rest.
            # This balances throughput with reliability.
            if chunk_index % 16 == 0:
                try:
                    await self._ble.request(data_pkt, timeout=REPLY_TIMEOUT)
                except Exception as exc:
                    self.state = DFUState.ERROR
                    raise DFUError(
                        f"DFU data chunk {chunk_index} failed at offset {offset}: {exc}"
                    ) from exc
            else:
                await self._ble.write_no_reply(data_pkt)
                # Small delay to avoid overwhelming the BLE stack
                await asyncio.sleep(0.01)

            offset += len(chunk)
            chunk_index += 1
            self._emit(offset, total)

        # ------------------------------------------------------------------
        # WR_INFO: send firmware metadata (size, CRC)
        # ------------------------------------------------------------------
        self.state = DFUState.WR_INFO
        self._emit(total, total)

        fw_crc = _crc16_xmodem(fw)
        info_payload = struct.pack("<IH", total, fw_crc)
        info_pkt = self._make_packet(CMD_DFU_DATA, 0xFF, info_payload)
        try:
            await self._ble.request(info_pkt, timeout=REPLY_TIMEOUT)
        except Exception as exc:
            self.state = DFUState.ERROR
            raise DFUError(f"DFU write info failed: {exc}") from exc

        # ------------------------------------------------------------------
        # DFU_VERIFY: request on-device verification
        # ------------------------------------------------------------------
        self.state = DFUState.DFU_VERIFY
        self._emit(total, total)

        verify_pkt = self._make_packet(CMD_DFU_VERIFY, 0x00)
        try:
            reply = await self._ble.request(verify_pkt, timeout=REPLY_TIMEOUT * 2)
        except Exception as exc:
            self.state = DFUState.ERROR
            raise DFUError(f"DFU verify request failed: {exc}") from exc

        # ------------------------------------------------------------------
        # DFU_ACTIVE: device is applying the firmware (may take a few seconds)
        # ------------------------------------------------------------------
        self.state = DFUState.DFU_ACTIVE
        self._emit(total, total)

        # Wait for device to reboot / apply (device will disconnect then reconnect)
        await asyncio.sleep(3.0)

        # ------------------------------------------------------------------
        # VER_DONE: confirm new version is running
        # ------------------------------------------------------------------
        self.state = DFUState.VER_DONE
        self._emit(total, total)

        if reply.arg != 0x01:
            self.state = DFUState.ERROR
            raise DFUError(
                f"DFU verification failed on device (arg=0x{reply.arg:02X})"
            )

        # ------------------------------------------------------------------
        # DONE
        # ------------------------------------------------------------------
        self.state = DFUState.DONE
        self._emit(total, total)


async def flash_firmware(
    address: str,
    fw_path: str | Path,
    on_progress: Callable[[int, int, DFUState], None] | None = None,
) -> None:
    """Flash a firmware file to a scooter over BLE.

    Args:
        address:     BLE MAC address (or UUID on macOS) of the target scooter.
        fw_path:     Path to a firmware .zip or raw .bin file.
        on_progress: Optional callback invoked on each progress update.
                     Signature: (bytes_sent: int, total_bytes: int, state: DFUState)

    Raises:
        FileNotFoundError: if fw_path does not exist.
        DFUError:          if the DFU process fails at any stage.
        RuntimeError:      if the BLE connection cannot be established.
        ImportError:       if bleak is not installed.
    """
    _require_bleak()

    fw_data = _load_firmware(fw_path)

    async with ScooterBLE(address) as ble:
        session = _DFUSession(ble=ble, fw_data=fw_data, on_progress=on_progress)
        await session.run()


# ---------------------------------------------------------------------------
# BLE scanner helper
# ---------------------------------------------------------------------------


async def scan_for_scooters(timeout: float = 5.0) -> list[dict]:
    """Scan for nearby BLE devices that look like Ninebot/Xiaomi scooters.

    Returns a list of dicts with keys: address, name, rssi, protocol.

    Raises:
        ImportError: if bleak is not installed.
    """
    _require_bleak()

    results: list[dict] = []

    devices = await BleakScanner.discover(timeout=timeout)
    for device in devices:
        name = (device.name or "").lower()
        uuids = list(device.metadata.get("uuids", []))

        if any(kw in name for kw in ("ninebot", "segway", "m365", "mi scooter", "xiaomi")):
            proto = _detect_protocol(uuids)
            results.append(
                {
                    "address": device.address,
                    "name": device.name or "",
                    "rssi": device.rssi,
                    "protocol": proto.value,
                }
            )
        elif any(
            NB_SERVICE_UUID.lower() in u.lower() or
            MI_SERVICE_UUID.lower() in u.lower() or
            MI_ALT_SERVICE_UUID.lower() in u.lower()
            for u in uuids
        ):
            proto = _detect_protocol(uuids)
            results.append(
                {
                    "address": device.address,
                    "name": device.name or "",
                    "rssi": device.rssi,
                    "protocol": proto.value,
                }
            )

    results.sort(key=lambda d: d["rssi"], reverse=True)
    return results
