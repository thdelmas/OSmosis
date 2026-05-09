# Torrent Trackers & Indexers for OSmosis

A curated list of torrent sources useful for finding the raw material OSmosis
revives: stock firmware archives, custom ROMs, recovery images, Linux ISOs for
old hardware, and abandoned vendor software.

This is a research/reference document. OSmosis does not redistribute via
torrent itself — see the **[Articulation with IPFS](#articulation-with-ipfs)**
section for how torrents and IPFS chain together.

---

## Why this list exists

Two of the trackers French users historically relied on for firmware and
device archives are dead:

- **T411** — seized and shut down in 2017.
- **YGG / YggTorrent** — domain seizures and ISP blocks killed it (the latest
  iteration is no longer reachable as of 2026).

Without a single dominant French tracker, finding old/abandoned firmware now
means knowing where the long-tail communities still live. This doc keeps that
knowledge in one place so OSmosis users (and contributors backfilling the IPFS
catalog) know where to look first.

---

## Public trackers — Linux and FOSS distros

Lowest legal risk; best for SBC / laptop / retro-handheld OS images.

### LinuxTracker
- Site: `https://linuxtracker.org/`
- Pure Linux distros, including niche/old releases that have rotated off
  official mirrors.
- Useful for: archived Debian/Ubuntu/Fedora point releases, distros for
  pre-PAE/i386/armv7 hardware that modern mirrors no longer carry.

### Internet Archive
- Site: `https://archive.org/`
- Many firmware/ISO uploads expose a `.torrent` file alongside HTTP.
- BitTorrent here is the official Archive-backed swarm — legitimate and
  long-lived.
- Useful for: stock OEM firmware uploads, recovery archives, historical
  software (e.g. early Android factory images, vendor utility CDs).

### DistroWatch
- Site: `https://distrowatch.com/`
- Not a tracker, but every distro page links to torrents/HTTP/IPFS where
  available.
- Useful as the *index of indexes* before falling back to public trackers.

---

## Public trackers — general / firmware-adjacent

Mixed legality depending on jurisdiction and content. Useful for finding
abandoned/orphaned firmware that is no longer hosted by the OEM.

### RuTracker
- Site: `https://rutracker.org/`
- Russian-language but huge firmware/software section (ПО → Драйверы и
  прошивки). Often the only place an obscure 2010-era OEM ROM still seeds.
- Requires free registration.

### 1337x
- Site: `https://1337x.to/`
- General-purpose. Reasonable signal for popular custom ROMs and Linux distros;
  poor signal for niche firmware.

### The Pirate Bay
- Site: `https://thepiratebay.org/`
- Old uploads survive here long after they vanish elsewhere. Worth a search
  when chasing a specific ROM filename or firmware hash.

### Nyaa.si
- Site: `https://nyaa.si/`
- Primarily East-Asian media, but sometimes the only mirror for Japanese OEM
  firmware (Sharp, Panasonic, Casio embedded).

### TorrentGalaxy / SolidTorrents / BTDigg
- Aggregators / DHT search engines. Useful when you have a partial filename or
  a known SHA1 and want to find any swarm still seeding it.

---

## Defunct / replaced trackers (do not link)

Recorded so users searching for these names land on this doc instead of a
typo-squat.

| Tracker | Status | Replacement strategy |
|---|---|---|
| T411 | Seized 2017 | RuTracker + Archive.org for firmware; LinuxTracker for distros |
| YGG / YggTorrent | Domain seized / unreachable 2026 | Same as above; check 1337x for popular ROMs |
| Demonoid | Repeatedly resurrected and re-killed; not stable | Internet Archive + RuTracker |
| KickassTorrents | Dead 2016 | 1337x absorbed most of its firmware uploads |

Treat any "T411 reborn" or "new YGG" domain as untrusted until verified —
typo-squats targeting these names are common.

---

## Articulation with IPFS

Torrents and IPFS solve different halves of the same problem. OSmosis already
has a mature IPFS layer (see [`docs/project/IPFS-ROADMAP.md`](../project/IPFS-ROADMAP.md));
the trackers above feed *into* that layer.

### The two-stage pipeline

```
[ Torrent / HTTP / OEM site ]   ← bootstrap: someone, somewhere, has the bytes
            │
            ▼
   SHA256 verify against firmware registry
            │
            ▼
   ipfs add  →  pin to local IPFS node  →  index in ~/.osmosis/ipfs-index.json
            │
            ▼
[ IPFS swarm + signed manifests ]   ← preservation: content-addressed, replicable
```

- **Torrents are the discovery / bootstrap layer.** Mutable URLs, named
  trackers, swarms that come and go (T411 → YGG → ?). You use them once to get
  the bytes the first time.
- **IPFS is the preservation / community layer.** Once content is pinned and
  its CID is in a signed manifest, it no longer matters whether the original
  tracker survives. The content is addressed by hash, fetched from any peer,
  and verified against the firmware registry.

### Why we don't replace torrents with IPFS

We can't. IPFS only has what someone has pinned. The first user with a given
firmware blob has to get it from *somewhere* — OEM site, FTP archive, XDA
attachment, or a torrent. Torrents remain the long-tail answer for content
that the OEM has taken down and that nobody has yet pinned.

### Why we don't replace IPFS with torrents

Trackers die (T411, YGG, Demonoid, KAT). Magnet links survive only as long as
some peer in the DHT still has the data and is reachable. IPFS pinning
distributes durability across every OSmosis user who has fetched a given CID,
and signed manifests + the firmware registry let us verify content
independently of any tracker's reputation system.

### Concrete contributor flow

When you find a firmware/ROM via one of the trackers above:

1. Download the file (verify SHA256 against the OSmosis firmware registry if
   the device is already known).
2. From the IPFS storage panel: **Pin file** → record the CID.
3. If the device profile doesn't yet reference this CID, add it to the
   appropriate `profiles/<device>.yaml` or open a manifest contribution.
4. Optional: export a signed manifest (Tier 4.4) so other users can import
   your contribution under a trusted-publisher policy.
5. Optional: broadcast on the `osmosis-updates` PubSub topic (Tier 6.3) so
   online peers see the new content immediately.

After step 2, the original torrent becomes a fallback rather than a
dependency. After enough pins across the user base, the tracker can disappear
entirely without losing the firmware.

### What this means for tracker choice

Prefer trackers in this order when bootstrapping new content into the IPFS
catalog:

1. **Internet Archive** — stable, legal, often already mirrors what we need,
   and uploads survive long-term.
2. **LinuxTracker** — for distros, especially old/niche ones.
3. **RuTracker** — for obscure OEM firmware that nothing else carries.
4. **1337x / TPB / Nyaa** — last resort for one-off ROM hunts.

The whole point of pinning to IPFS afterwards is that we only need to do this
*once per file, ever* — independent of which tracker is alive that week.

---

## Maintenance

If a tracker on this list dies or is replaced, update it here AND record the
replacement in the "Defunct / replaced" table so future users can route past
the dead name. Treat tracker churn as a known failure mode — that's exactly
why the IPFS layer exists.
