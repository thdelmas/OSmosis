"""Android init.rc generators for LETHE services.

Extracted from lethe_build.py to keep files under the 500-line limit.
"""


def generate_burner_init_rc() -> str:
    """Generate the Android init.rc service for burner mode wipe-on-boot."""
    return """\
# Lethe burner mode — early-init wipe service
# Runs before zygote. Reads config from /persist partition.

on early-init
    # Mount persist partition to read burner mode preference
    mount ext4 /dev/block/bootdevice/by-name/persist /persist nosuid nodev noatime

on post-fs-data
    # Check burner mode toggle (stored on /persist, survives wipe)
    exec -- /system/bin/sh -c "\\
        ENABLED=$(getprop persist.lethe.burner.enabled); \\
        if [ \\"$ENABLED\\" = \\"true\\" ]; then \\
            log -t lethe-burner 'Burner mode active — wiping user data'; \\
            rm -rf /data/app /data/data /data/user /data/user_de /data/misc/wifi /data/misc/bluedroid; \\
            rm -rf /data/media/0/*; \\
            rm -rf /data/system/notification_log; \\
            settings put secure android_id $(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 16); \\
            log -t lethe-burner 'Wipe complete — booting clean session'; \\
        else \\
            log -t lethe-burner 'Burner mode disabled — normal boot'; \\
        fi"

service lethe-mac-rotate /system/bin/sh -c "\\
    ENABLED=$(getprop persist.lethe.burner.enabled); \\
    if [ \\"$ENABLED\\" = \\"true\\" ]; then \\
        MAC=$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 12 | sed 's/../&:/g;s/:$//'); \\
        ip link set wlan0 down; \\
        ip link set wlan0 address $MAC; \\
        ip link set wlan0 up; \\
        log -t lethe-burner \\"MAC rotated to $MAC\\"; \\
    fi"
    class late_start
    oneshot
    disabled

on property:sys.boot_completed=1
    start lethe-mac-rotate
"""


def generate_deadman_init_rc() -> str:
    """Generate the Android init.rc service for the dead man's switch.

    On boot, checks elapsed time since last check-in against the configured
    interval. If the deadline has passed, escalates through lock -> wipe -> brick.
    The timer is based on the hardware RTC, not network time, so powering off
    or pulling the SIM doesn't stall the countdown.
    """
    return """\
# Lethe dead man's switch — boot-time enforcement
# Runs after persist is mounted, before zygote.
# Reads /persist/lethe/deadman/ for config and heartbeat.

on post-fs-data
    exec -- /system/bin/sh -c "\\
        ENABLED=$(cat /persist/lethe/deadman.prop 2>/dev/null | grep 'persist.lethe.deadman.enabled=true'); \\
        if [ -z \\"$ENABLED\\" ]; then \\
            log -t lethe-deadman 'Dead man switch disabled — skipping'; \\
            exit 0; \\
        fi; \\
        \\
        INTERVAL_RAW=$(getprop persist.lethe.deadman.interval); \\
        INTERVAL_RAW=$${INTERVAL_RAW:-24h}; \\
        \\
        # Convert interval to seconds \\
        case \\"$INTERVAL_RAW\\" in \\
            12h) INTERVAL=43200 ;; \\
            24h) INTERVAL=86400 ;; \\
            48h) INTERVAL=172800 ;; \\
            72h) INTERVAL=259200 ;; \\
            7d)  INTERVAL=604800 ;; \\
            *)   INTERVAL=86400 ;; \\
        esac; \\
        \\
        GRACE=$(getprop persist.lethe.deadman.grace_period); \\
        GRACE=$${GRACE:-4h}; \\
        case \\"$GRACE\\" in \\
            1h) GRACE_S=3600 ;; \\
            2h) GRACE_S=7200 ;; \\
            4h) GRACE_S=14400 ;; \\
            8h) GRACE_S=28800 ;; \\
            *)  GRACE_S=14400 ;; \\
        esac; \\
        \\
        DEADLINE=$((INTERVAL + GRACE_S)); \\
        \\
        # Read last check-in timestamp from persist \\
        HEARTBEAT_FILE=/persist/lethe/deadman/last_checkin; \\
        if [ ! -f \\"$HEARTBEAT_FILE\\" ]; then \\
            log -t lethe-deadman 'No heartbeat file — first boot, writing initial checkin'; \\
            mkdir -p /persist/lethe/deadman; \\
            date +%s > $HEARTBEAT_FILE; \\
            exit 0; \\
        fi; \\
        \\
        LAST_CHECKIN=$(cat $HEARTBEAT_FILE 2>/dev/null); \\
        NOW=$(date +%s); \\
        ELAPSED=$((NOW - LAST_CHECKIN)); \\
        \\
        log -t lethe-deadman \\"Last checkin: ${LAST_CHECKIN}, now: ${NOW}, elapsed: ${ELAPSED}s, deadline: ${DEADLINE}s\\"; \\
        \\
        if [ $ELAPSED -gt $DEADLINE ]; then \\
            log -t lethe-deadman 'DEADLINE EXCEEDED — escalating'; \\
            \\
            # Stage 1: Lock — force passphrase-only unlock \\
            log -t lethe-deadman 'Stage 1: Locking device (passphrase only)'; \\
            setprop persist.lethe.deadman.stage=locked; \\
            \\
            # Check if we've passed Stage 2 threshold (wipe) \\
            STAGE2_DELAY=3600; \\
            WIPE_DEADLINE=$((DEADLINE + STAGE2_DELAY)); \\
            if [ $ELAPSED -gt $WIPE_DEADLINE ]; then \\
                log -t lethe-deadman 'Stage 2: WIPING user data'; \\
                setprop persist.lethe.deadman.stage=wiped; \\
                rm -rf /data/app /data/data /data/user /data/user_de; \\
                rm -rf /data/misc/wifi /data/misc/bluedroid; \\
                rm -rf /data/media/0/*; \\
                rm -rf /data/system/notification_log; \\
                log -t lethe-deadman 'Wipe complete'; \\
                \\
                # Check if Stage 3 (brick) is enabled and threshold passed \\
                STAGE3_ENABLED=$(getprop persist.lethe.deadman.stage3.enabled); \\
                STAGE3_DELAY=7200; \\
                BRICK_DEADLINE=$((WIPE_DEADLINE + STAGE3_DELAY)); \\
                if [ \\"$STAGE3_ENABLED\\" = \\"true\\" ] && [ $ELAPSED -gt $BRICK_DEADLINE ]; then \\
                    log -t lethe-deadman 'Stage 3: BRICKING — overwriting critical partitions'; \\
                    setprop persist.lethe.deadman.stage=bricked; \\
                    dd if=/dev/urandom of=/dev/block/bootdevice/by-name/boot bs=4096 count=1024 2>/dev/null; \\
                    dd if=/dev/urandom of=/dev/block/bootdevice/by-name/recovery bs=4096 count=1024 2>/dev/null; \\
                    rm -rf /persist/lethe; \\
                    log -t lethe-deadman 'Brick complete — device unbootable without OSmosis USB recovery'; \\
                    reboot; \\
                fi; \\
            fi; \\
        else \\
            log -t lethe-deadman \\"Within deadline — $((DEADLINE - ELAPSED))s remaining\\"; \\
        fi"

# Runtime check-in service — runs periodically while the device is on.
# Monitors the heartbeat file and triggers the silent notification
# when a check-in is due.
service lethe-deadman-monitor /system/bin/sh -c "\\
    while true; do \\
        ENABLED=$(getprop persist.lethe.deadman.enabled); \\
        if [ \\"$ENABLED\\" != \\"true\\" ]; then \\
            sleep 3600; \\
            continue; \\
        fi; \\
        \\
        HEARTBEAT_FILE=/persist/lethe/deadman/last_checkin; \\
        LAST_CHECKIN=$(cat $HEARTBEAT_FILE 2>/dev/null || echo 0); \\
        NOW=$(date +%s); \\
        ELAPSED=$((NOW - LAST_CHECKIN)); \\
        \\
        INTERVAL_RAW=$(getprop persist.lethe.deadman.interval); \\
        case \\"$INTERVAL_RAW\\" in \\
            12h) INTERVAL=43200 ;; \\
            24h) INTERVAL=86400 ;; \\
            48h) INTERVAL=172800 ;; \\
            72h) INTERVAL=259200 ;; \\
            7d)  INTERVAL=604800 ;; \\
            *)   INTERVAL=86400 ;; \\
        esac; \\
        \\
        if [ $ELAPSED -ge $INTERVAL ]; then \\
            log -t lethe-deadman 'Check-in due — posting notification'; \\
            am broadcast -a lethe.intent.CHECKIN_DUE --ez overdue true; \\
        fi; \\
        \\
        sleep 900; \\
    done"
    class late_start
    oneshot
    disabled

on property:sys.boot_completed=1
    start lethe-deadman-monitor

# Duress PIN handler — triggered by the lock screen when the duress
# code is entered. Shows a fake home screen while wiping in background.
on property:persist.lethe.deadman.duress_triggered=true
    exec -- /system/bin/sh -c "\\
        log -t lethe-deadman 'DURESS PIN entered — silent wipe initiated'; \\
        rm -rf /data/app /data/data /data/user /data/user_de; \\
        rm -rf /data/misc/wifi /data/misc/bluedroid; \\
        rm -rf /data/media/0/*; \\
        rm -rf /data/system/notification_log; \\
        # Reset the duress flag so it doesn't re-trigger on next boot \\
        setprop persist.lethe.deadman.duress_triggered false; \\
        log -t lethe-deadman 'Duress wipe complete — device appears normal'"
"""
