# Fenrir Wallpapers — Volume 03

**Library navigation:** [Hub documentation](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/docs/README.md) · [Live volume registry](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/manifest/volumes.json) · [Fenrir project map](https://github.com/sunxsaturn/Fenrir-Arch/blob/main/docs/PROJECT-MAP.md) · [Desktop multi-volume sync](https://github.com/sunxsaturn/Fenrir-Dots/blob/main/docs/WALLPAPER-LIBRARY.md)

A public overflow image-storage volume in the combined Fenrir wallpaper library. Its current role is **balanced population**: add unique images to the categories that are most underrepresented across all active volume manifests.

## Current role and balancing

The hub registry currently marks Volume 03 as active and acquisition-enabled for balanced population.

The target is dynamic, not a fixed historical image count:

1. Read committed image records from every active volume manifest.
2. Find the current largest global category count.
3. Estimate how many complete equal-count rounds fit within the remaining shared repository capacity, using observed category image sizes.
4. Prioritize the most underrepresented categories and preserve a safety reserve.
5. Stop when no additional complete equal-count round fits or eligible source material is exhausted.

The registry is authoritative for the active balancing rule. Manifests are authoritative for actual files and counts. Do not copy old baseline counts into current documentation or code.

## Storage and acquisition limits

- Git object-store target: **8 GiB**.
- New image limit: **45 MiB**.
- Acquisition batch: up to **80 images / 700 MiB**.
- The repository uses dynamic shared capacity; there are no fixed per-category folder quotas in the current registry policy.
- A 512 MiB safety reserve protects repository metadata and size variance.
- Cross-volume SHA-256 and source-title de-duplication are required.
- Images must be landscape, at least 2560×1440, and JPEG, PNG or WebP.
- Only Public Domain, CC0, CC BY and CC BY-SA metadata pass the automated license gate; NC and ND are excluded.

No existing image is deleted, overwritten or moved to balance the collection.

## Coordinated schedule

Guarded population windows run at **00:17 and 12:17 UTC** only when Volume 02 has no active or queued acquisition run. The workflow checks the other public volume's Actions state before starting, keeping Wikimedia acquisition serialized across the library.

The live hub registry is authoritative for current schedule, role and storage policy. Both the source API's rate limits and each asset's individual license/attribution requirements remain in force.

## Categories

Nordic mythology and fantasy; cinematic nature; cosmic science fiction; Arctic blue and violet; monochrome futuristic architecture; red and violet dark fantasy; deep ocean and bioluminescence; obsidian minimalism and abstract geometry; unsorted.

## Clone and synchronize

```bash
git clone --depth=1 https://github.com/sunxsaturn/Fenrir-Wallpapers-03.git ~/Pictures/Fenrir-Wallpapers-03
```

For the complete collection, let Fenrir Dots discover every active volume from the hub registry:

```bash
fenrir-wallpaper sync-library --dry-run
fenrir-wallpaper sync-library
```

## Rights and attribution

Every public image retains its creator/credit, source page, license identifier and URL, dimensions, MIME type and SHA-256 in the volume manifest. Automated metadata screening is not a legal warranty. Verify original source pages and additional rights notices before reuse.
