# Fenrir Wallpapers — Volume 03

A public image-storage volume in the combined Fenrir wallpaper library.

**Current collection:** the live wallpaper count is recorded in [manifest/index.json](./manifest/index.json). The authoritative list of volumes is [the hub registry](https://github.com/sunxsaturn/Fenrir-Wallpapers/blob/main/manifest/volumes.json).

## Storage and acquisition

- Target Git object store: **8 GiB**.
- Individual image limit: **45 MiB**.
- Acquisition batch: up to **80 images / 700 MiB**.
- Themed category folders target **700 MiB each**; **Unsorted** targets **512 MiB**. The repository-wide 8 GiB limit is always authoritative.
- Batches prioritize the least-filled folders and rotate tie order.
- Scheduled sequential Wikimedia Commons acquisition, coordinated as the library's only scheduled downloader.
- Cross-volume SHA-256 and source-title de-duplication against every active Fenrir volume.
- Image minimum: 2560×1440 landscape; JPEG, PNG or WebP.
- Only Public Domain, CC0, CC BY and CC BY-SA metadata pass the automated license gate. NC and ND terms are excluded.
- Creator, attribution, source page, license, dimensions and SHA-256 are retained for every published image.

The importer respects source rate limits, backs off on HTTP 429, validates decoded image bytes and stops before exceeding storage budgets. Automated metadata screening is not a legal warranty. All images are stored under [Fenrir Wallpapers/](./Fenrir%20Wallpapers/).

## Categories

Nordic mythology and fantasy; cinematic nature; cosmic science fiction; Arctic blue and violet; monochrome futuristic architecture; red and violet dark fantasy; deep ocean and bioluminescence; obsidian minimalism and abstract geometry; unsorted.

## Clone

```bash
git clone --depth=1 https://github.com/sunxsaturn/Fenrir-Wallpapers-03.git ~/Pictures/Fenrir-Wallpapers-03
```

Use the hub registry to discover every active volume. Volume 01 remains archived at its original conservative budget. Volume 02's scheduled acquisition is paused while this volume runs the single scheduled Commons acquisition coordinator; its existing files remain unchanged.

## Rights and attribution

Every published file retains its Wikimedia Commons source page, creator/credit, license identifier and URL, dimensions, MIME type and SHA-256. Non-commercial, no-derivatives, missing-attribution and unsupported license records are excluded. Verify each source page and any additional rights notices before reuse.
