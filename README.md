# Fenrir Wallpapers — Volume 03

**Library navigation:** [Hub documentation](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/docs/README.md) · [Closed population status](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/docs/POPULATION-STATUS.md) · [Live volume registry](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/manifest/volumes.json) · [Desktop sync guide](https://github.com/sunxsaturn/Fenrir-Dots/blob/main/docs/WALLPAPER-LIBRARY.md)

Volume 03 is a published, immutable image-storage volume in the Fenrir public wallpaper library. It contains **605 committed wallpapers** and remains active for desktop synchronization.

## Population status

**Closed on 2026-11-27.** The scheduled and manual acquisition workflow has been removed. No new source acquisition, category balancing, image-count quota or extra volume is planned. Existing files and manifest records remain unchanged and available to registry-driven desktop sync.

## Existing storage and rights

- All published image files use content-addressed names and remain in their committed category folders.
- Cross-volume SHA-256 de-duplication was checked against the current three-volume library.
- Public images retain creator/credit, source, attribution, license, dimensions, MIME type and integrity metadata.
- The committed manifest is authoritative for the volume's current image records.
- No image is deleted, overwritten, moved or copied into another category to make counts equal.
- Existing licenses and source/provider requirements still apply; publication does not grant additional reuse rights.

## Categories

Arctic blue/violet; cinematic nature; cosmic science fiction; deep ocean/bioluminescence; monochrome futuristic architecture; Nordic mythology/fantasy; obsidian minimalism/abstract geometry; red/violet dark fantasy; unsorted.

## Synchronize the complete library

Do not clone a hard-coded volume list. Let Fenrir Dots read the hub registry:

```bash
fenrir-wallpaper audit-library --json
fenrir-wallpaper sync-library --dry-run
fenrir-wallpaper sync-library
```

The audit checks manifests only; the preview is read-only. The separately confirmed sync downloads already-published manifest entries, verifies downloaded bytes and preserves existing local files.

See the [hub population status](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/docs/POPULATION-STATUS.md) for the 1,871-image library snapshot and category distribution.
