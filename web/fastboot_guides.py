"""OEM bootloader unlock guidance for fastboot operations."""

UNLOCK_GUIDES = {
    "google": {
        "brand": "Google Pixel",
        "steps": [
            "Enable Developer Options: Settings > About Phone > tap Build Number 7 times",
            "Enable OEM Unlocking: Settings > Developer Options > OEM Unlocking",
            "Boot to fastboot: Power off, then hold Power + Volume Down",
            "Run: fastboot flashing unlock",
            "Confirm on device with Volume keys + Power",
        ],
        "notes": "All data will be erased. Google Pixels have no waiting period.",
    },
    "oneplus": {
        "brand": "OnePlus",
        "steps": [
            "Enable Developer Options: Settings > About Phone > tap Build Number 7 times",
            "Enable OEM Unlocking: Settings > Developer Options > OEM Unlocking",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run: fastboot oem unlock",
            "Confirm on device",
        ],
        "notes": "OnePlus devices unlock instantly. Data will be erased.",
    },
    "xiaomi": {
        "brand": "Xiaomi / Poco / Redmi",
        "steps": [
            "Apply for unlock at en.miui.com/unlock (requires Mi account)",
            "Wait for approval (typically 72 hours to 30 days)",
            "Download Mi Unlock tool (Windows) or use unofficial Linux tools",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run the unlock tool with your Mi account credentials",
        ],
        "notes": "Xiaomi enforces a waiting period. Cannot be unlocked instantly.",
    },
    "samsung": {
        "brand": "Samsung (limited fastboot)",
        "steps": [
            "Samsung uses Download Mode + Heimdall/Odin, not fastboot",
            "For Knox-tripped devices: OEM unlock is permanently disabled",
            "Check Knox status: Settings > About Phone > Status > Knox Warranty Void",
        ],
        "notes": "Most Samsung devices do not support fastboot. Use Heimdall instead.",
    },
    "fairphone": {
        "brand": "Fairphone",
        "steps": [
            "Enable Developer Options and OEM Unlocking",
            "Boot to fastboot: Power off, hold Power + Volume Down",
            "Run: fastboot flashing unlock",
            "Confirm on device",
        ],
        "notes": "Fairphone actively supports unlocking and alternative OSes.",
    },
    "motorola": {
        "brand": "Motorola",
        "steps": [
            "Apply for unlock code at motorola.com/unlocking-bootloader",
            "Enable Developer Options and OEM Unlocking",
            "Boot to fastboot, run: fastboot oem get_unlock_data",
            "Submit the unlock data on the Motorola website",
            "Receive unlock code via email",
            "Run: fastboot oem unlock <code>",
        ],
        "notes": "Requires a Motorola account and carrier approval. Not all models supported.",
    },
}
