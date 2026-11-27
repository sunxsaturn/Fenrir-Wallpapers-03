#!/usr/bin/env python3
"""Populate the Fenrir image repository from individually licensed Commons files.

Only original files with explicit free/public-domain license metadata are
considered. Full-resolution bytes are validated before publication. The job
keeps the 8 GiB Git-object budget, tracks attribution, and never uploads
Catalog databases or private quarantine data.
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import html
import io
import json
import re
import time
import warnings
from urllib.error import HTTPError
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "FenrirWallpaperLibrary/1.0 "
    "(https://github.com/sunxsaturn/Fenrir-Wallpapers-03; "
    "Commons reuse with per-file attribution)"
)
ROOT = Path.cwd()
IMAGE_ROOT = ROOT / "Fenrir Wallpapers"
INDEX_PATH = ROOT / "manifest/index.json"
MAX_REPOSITORY_BYTES = 8 * 1024 * 1024 * 1024
MAX_IMAGE_BYTES = 45 * 1024 * 1024
MAX_DOWNLOAD_BYTES_PER_RUN = 700 * 1024 * 1024
MAX_DOWNLOAD_ATTEMPTS_PER_RUN = 220
MAX_SEARCH_PAGES_PER_CATEGORY_PER_RUN = 24
PAGE_SIZE = 50
PER_CATEGORY_LIMIT = 16
MIME_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
CATEGORIES = {
    "nordic-mythology-fantasy": [
        "Norse mythology",
        "Viking ship landscape",
        "Viking age archaeology",
        "Viking Age runestone",
        "Norse mythology sculpture",
        "Scandinavian stave church",
        "Viking burial mound landscape",
        "Norse mythology museum artifact",
        "Viking longship reconstruction",
        "Norse runestone landscape",
        "Viking age archaeological site",
        "Scandinavian Viking ship museum",
        "Norse mythology public domain artwork",
    ],
    "cinematic-nature": [
        "fjord mountain landscape",
        "mountain range landscape",
        "waterfall forest landscape",
    ],
    "cosmic-science-fiction": [
        "nebula galaxy astrophotography",
        "Hubble space telescope galaxy",
        "Milky Way night sky",
    ],
    "arctic-blue-violet": [
        "aurora borealis landscape",
        "glacier ice field landscape",
        "iceberg Antarctica landscape",
        "blue glacier aerial photography",
        "polar blue ice landscape",
        "Antarctic blue iceberg photography",
        "arctic night blue landscape",
        "frozen sea blue ice photography",
        "blue glacier ice photography",
        "iceberg blue ice photography",
        "aurora night landscape",
        "polar landscape blue ice",
        "glacial ice cave blue",
        "ice fjord aerial photography",
        "Greenland glacier landscape",
        "Antarctic ice shelf landscape",
        "winter mountain blue hour",
        "frozen lake blue landscape",
        "Arctic ocean iceberg photography",
        "snow mountain night sky",
        "blue ice cave photography",
        "alpine glacier lake",
        "Norway northern lights photography",
        "glacier calving photography",
        "Svalbard arctic landscape",
    ],
    "monochrome-futuristic-architecture": [
        "brutalist architecture",
        "modern architecture geometric facade",
        "concrete architecture monochrome",
    ],
    "red-violet-dark-fantasy": [
        "volcanic landscape",
        "red rock canyon landscape",
        "red nebula astronomy",
    ],
    "deep-ocean-bioluminescence": [
        "bioluminescence underwater",
        "coral reef underwater",
        "underwater ocean photography",
        "deep sea bioluminescence",
        "blue jellyfish underwater photography",
        "deep ocean exploration ROV",
        "underwater cave blue water",
        "blue underwater seascape photography",
        "deep sea creatures blue water",
        "underwater ocean floor blue",
    ],
    "obsidian-minimalism-abstract-geometry": [
        "abstract black geometric sculpture",
        "brutalist architecture modernist",
        "modern architecture geometric minimalism",
        "black minimalist architecture",
        "dark geometric sculpture",
        "black and white brutalist architecture",
        "monolithic black architecture",
        "minimalist black geometric art",
        "black monolithic sculpture photography",
        "dark minimalist concrete architecture",
        "black geometric installation art",
        "monochrome geometric interior architecture",
        "dark abstract architectural photography",
        "black and white modernist architecture photography",
        "brutalist concrete facade monochrome",
        "minimalist dark geometric building exterior",
        "black abstract sculpture photography",
        "monolithic concrete architecture black white",
        "geometric shadow architecture monochrome",
        "dark brutalist building photography",
        "minimalist black architecture panorama",
        "black concrete architecture photography",
        "minimalist brutalist architecture",
        "monolithic architecture black",
        "geometric concrete building",
        "modernist architecture shadows",
        "black geometric sculpture photography",
        "dark architectural interior",
        "concrete staircase architecture",
        "brutalist building facade",
        "minimalist concrete architecture",
        "monochrome architecture photography",
        "geometric shadow building",
        "architectural concrete detail",
        "black abstract sculpture",
        "dark geometric installation",
        "modernist concrete facade",
        "black geometric building exterior",
        "brutalist architecture detail photography",
        "minimalist architecture black white",
        "geometric concrete architecture",
    ],
    "unsorted": [
        "dark cinematic landscape photography",
        "abstract dark wallpaper background",
        "night landscape panorama photography",
        "blue violet atmospheric photography",
        "dark blue abstract landscape",
        "cinematic night sky panoramic photography",
        "dark abstract architecture photography",
        "blue violet abstract background photography",
        "dark monochrome abstract geometry",
        "purple night landscape panorama",
        "black minimal abstract background",
        "blue hour mountain and ocean landscape",
        "dark futuristic architecture panorama",
        "violet atmospheric night photography",
        "blue hour landscape photography",
        "night sky landscape photography",
        "dark forest landscape photography",
        "nocturnal cityscape photography",
        "storm clouds mountain landscape",
        "midnight ocean photography",
        "dark misty mountain landscape",
        "black and white landscape panorama",
        "blue violet landscape photography",
        "dark coastal landscape night",
        "night mountain panorama",
        "starry sky mountains photography",
        "dark abstract photographic art",
        "minimalist dark landscape",
        "blue hour urban photography",
        "dark sky panorama photography",
        "night ocean coastline photography",
        "cinematic mountain night photography",
        "deep blue night landscape",
        "dark nature panorama photography",
        "moonlit landscape photography",
        "cloudy night sky landscape",
        "blue twilight mountain landscape",
        "nocturnal forest panorama",
    ],
}
LICENSE_RE = re.compile(r"^CC BY(?:-SA)?(?:\s|$)", re.IGNORECASE)
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MIN_REQUEST_INTERVAL = 2.0
LAST_REQUEST_AT = 0.0


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    if not isinstance(value, str):
        return ""
    parser = TextOnly()
    try:
        parser.feed(value)
        parser.close()
        return " ".join(html.unescape(" ".join(parser.parts)).split())
    except Exception:
        return " ".join(re.sub(r"<[^>]*>", " ", html.unescape(value)).split())


def open_polite(request: Request, timeout: int):
    """Rate-limit all Commons API and image requests; back off on HTTP 429."""
    global LAST_REQUEST_AT
    for attempt in range(3):
        delay = MIN_REQUEST_INTERVAL - (time.monotonic() - LAST_REQUEST_AT)
        if delay > 0:
            time.sleep(delay)
        LAST_REQUEST_AT = time.monotonic()
        try:
            return urlopen(request, timeout=timeout)
        except HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After", "30")
            try:
                wait_seconds = int(retry_after)
            except (TypeError, ValueError):
                wait_seconds = 30
            time.sleep(min(120, max(30, wait_seconds)))
    raise RuntimeError("Commons request retry loop ended unexpectedly")


def get_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with open_polite(request, timeout=45) as response:
        payload = response.read(12 * 1024 * 1024 + 1)
    if len(payload) > 12 * 1024 * 1024:
        raise ValueError("Commons API response exceeded 12 MiB")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Commons API returned a non-object response")
    if "error" in value:
        raise ValueError(f"Commons API error: {value['error']}")
    return value


def fetch_search_page(query: str, offset: int) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(PAGE_SIZE),
        "gsroffset": str(offset),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
    }
    url = API + "?" + urlencode(params)
    data = get_json(url)
    query_data = data.get("query", {})
    pages = query_data.get("pages", [])
    return pages if isinstance(pages, list) else []


def license_details(ext: dict) -> tuple[str, str] | None:
    name = clean(ext.get("LicenseShortName"))
    lowered = name.lower()
    license_url = clean(ext.get("LicenseUrl"))
    if "non-commercial" in lowered or "noncommercial" in lowered:
        return None
    if re.search(r"\bNC\b|\bND\b", name, re.IGNORECASE):
        return None
    if lowered.startswith("cc0"):
        return name, license_url or "https://creativecommons.org/publicdomain/zero/1.0/"
    if lowered == "public domain" or lowered.startswith("pd-"):
        return name, license_url or "https://commons.wikimedia.org/wiki/Commons:Public_domain"
    if LICENSE_RE.match(name):
        if not license_url.startswith("https://"):
            return None
        return name, license_url
    return None


def image_bytes(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("image URL is not HTTPS")
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/jpeg,image/png,image/webp",
        },
    )
    with open_polite(request, timeout=90) as response:
        content_type = response.headers.get_content_type().lower()
        if content_type not in MIME_SUFFIX:
            raise ValueError(f"unsupported response MIME type: {content_type}")
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_IMAGE_BYTES:
            raise ValueError("image exceeds per-file size limit")
        payload = response.read(MAX_IMAGE_BYTES + 1)
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("image is empty or exceeds per-file size limit")
    return payload


def color_family(rgb: tuple[int, int, int]) -> str:
    red, green, blue = (channel / 255.0 for channel in rgb)
    hue, saturation, brightness = colorsys.rgb_to_hsv(red, green, blue)
    degrees = hue * 360.0
    if brightness >= 0.88 and saturation <= 0.20:
        return "white"
    if saturation <= 0.18:
        return "black" if brightness <= 0.14 else "neutral"
    if degrees < 15 or degrees >= 345:
        return "red"
    if 15 <= degrees < 43:
        return "brown" if brightness <= 0.78 else "orange"
    if 43 <= degrees < 70:
        return "yellow"
    if 70 <= degrees < 165:
        return "green"
    if 165 <= degrees < 260:
        return "blue"
    if 260 <= degrees < 330:
        return "purple"
    return "red"


def validate_image(payload: bytes, mime: str) -> tuple[int, int, list[str]]:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(payload)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("decoded image format is not JPEG, PNG or WebP")
            image = ImageOps.exif_transpose(source)
            width, height = image.size
            if width < 2560 or height < 1440 or width <= height:
                raise ValueError("image does not meet 2560x1440 landscape minimum")
            image.load()
            sample = image.convert("RGB")
            sample.thumbnail((128, 128), Image.Resampling.BOX)
            colors = sample.getcolors(maxcolors=128 * 128)
            if colors is None:
                raise ValueError("could not compute bounded palette")
            dominant = sorted(colors, key=lambda row: (-row[0], row[1]))[:5]
            hex_colors = [
                "#" + "".join(f"{channel:02x}" for channel in rgb)
                for _count, rgb in dominant
            ]
            families = {color_family(rgb) for _count, rgb in dominant}
            excluded = families.intersection({"yellow", "orange", "brown"})
            if excluded:
                raise ValueError("image violates Fenrir palette policy: " + ",".join(sorted(excluded)))
            expected = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }[source.format]
            if expected != mime:
                raise ValueError("decoded format does not match Commons MIME metadata")
    return width, height, hex_colors


def load_index() -> dict:
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {
            "schema": "org.fenrir.public-wallpapers.index.v1",
            "updated_at": None,
            "count": 0,
            "search_state": {},
            "items": [],
        }
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "org.fenrir.public-wallpapers.index.v1"
        or not isinstance(payload.get("items"), list)
    ):
        raise ValueError("existing manifest/index.json has an invalid schema")
    if not isinstance(payload.get("search_state", {}), dict):
        payload["search_state"] = {}
    return payload


def git_object_bytes() -> int:
    import subprocess

    result = subprocess.run(
        ["git", "count-objects", "-v"],
        check=True,
        text=True,
        capture_output=True,
    )
    values = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip()
    return (
        int(values.get("size", "0")) + int(values.get("size-pack", "0"))
    ) * 1024


def commons_page_url(title: str) -> str:
    return "https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_"), safe="()_:")


VOLUME_REGISTRY_URL = "https://raw.githubusercontent.com/sunxsaturn/Fenrir-Wallpapers/main/manifest/volumes.json"


def normalize_title(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.removeprefix("File:").replace("_", " ").split()).casefold()


def fetch_public_json(url: str) -> dict:
    if not url.startswith("https://raw.githubusercontent.com/"):
        raise ValueError("volume manifests must use raw.githubusercontent.com HTTPS")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=40) as response:
        raw = response.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError("volume manifest exceeded 64 MiB")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("volume manifest is not a JSON object")
    return payload


def gather_library_deduplication(
    local_index: dict,
) -> tuple[set[str], set[str], dict[str, int], dict[str, int]]:
    """Read all active volumes and count unique assets and bytes by category."""
    known_shas: set[str] = set()
    known_titles: set[str] = set()
    category_counts: dict[str, int] = {}
    category_bytes: dict[str, int] = {}
    counted_assets: set[str] = set()

    def absorb(payload: dict) -> None:
        records = payload.get("items")
        if not isinstance(records, list):
            raise ValueError("volume manifest has no items array")
        for item in records:
            if not isinstance(item, dict):
                continue
            digest = item.get("sha256")
            valid_digest = isinstance(digest, str) and SHA_RE.fullmatch(digest)
            if valid_digest:
                known_shas.add(digest)
            title = normalize_title(item.get("title") or item.get("commons_title"))
            if title:
                known_titles.add(title)

            item_path = item.get("path")
            if not isinstance(item_path, str):
                continue
            parts = Path(item_path).parts
            if len(parts) < 3 or parts[0] != "Fenrir Wallpapers":
                continue
            category = parts[1]
            if category not in CATEGORIES:
                continue
            identity = digest if valid_digest else (f"title:{title}" if title else f"path:{item_path}")
            if identity in counted_assets:
                continue
            counted_assets.add(identity)
            category_counts[category] = category_counts.get(category, 0) + 1
            item_size = item.get("file_size_bytes")
            if isinstance(item_size, int) and not isinstance(item_size, bool) and item_size > 0:
                category_bytes[category] = category_bytes.get(category, 0) + item_size

    # The local index may contain uncommitted state; absorb it first. The
    # identity set prevents the same manifest being counted again via registry.
    absorb(local_index)
    registry = fetch_public_json(VOLUME_REGISTRY_URL)
    volumes = registry.get("volumes")
    if not isinstance(volumes, list) or not volumes:
        raise ValueError("hub registry has no volumes")
    for volume in volumes:
        if isinstance(volume, dict) and volume.get("active") is True:
            url = volume.get("manifest_url")
            if not isinstance(url, str):
                raise ValueError("registered volume has no manifest URL")
            absorb(fetch_public_json(url))
    return known_shas, known_titles, category_counts, category_bytes

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new-images", type=int, default=40)
    args = parser.parse_args()
    if not 1 <= args.max_new_images <= 80:
        raise SystemExit("--max-new-images must be between 1 and 80")

    index = load_index()
    existing_shas, existing_titles, global_category_counts, global_category_bytes = (
        gather_library_deduplication(index)
    )
    starting_global_max_count = max(
        (global_category_counts.get(category, 0) for category in CATEGORIES),
        default=0,
    )
    search_state = index.setdefault("search_state", {})
    # Shared repository storage is allocated to preserve equal image counts;
    # per-folder quotas do not constrain the common target.
    category_budgets = {category: MAX_REPOSITORY_BYTES for category in CATEGORIES}
    folder_usage = {category: 0 for category in CATEGORIES}
    for item in index["items"]:
        if not isinstance(item, dict):
            continue
        item_path = item.get("path")
        item_size = item.get("file_size_bytes")
        if (
            isinstance(item_path, str)
            and item_path.startswith("Fenrir Wallpapers/")
            and isinstance(item_size, int)
            and item_size > 0
        ):
            parts = Path(item_path).parts
            if len(parts) >= 3 and parts[1] in folder_usage:
                folder_usage[parts[1]] += item_size
    category_names = list(CATEGORIES)
    try:
        category_start = int(search_state.get("_category_start", 0)) % len(category_names)
    except (TypeError, ValueError):
        category_start = 0
    rotated_categories = category_names[category_start:] + category_names[:category_start]
    # Give the least-filled folders first access to each batch; the rotating
    # tie-breaker prevents stable dictionary order from starving a category.
    ordered_categories = sorted(
        rotated_categories,
        key=lambda name: (
            global_category_counts.get(name, 0),
            folder_usage[name] / category_budgets[name],
        ),
    )
    start_size = git_object_bytes()
    available_budget = MAX_REPOSITORY_BYTES - start_size
    repository_safety_reserve = 512 * 1024 * 1024
    usable_budget = max(0, available_budget - repository_safety_reserve)
    average_image_bytes = {
        category: max(
            1,
            int(
                global_category_bytes.get(category, 0)
                / max(1, global_category_counts.get(category, 0))
            ),
        )
        for category in CATEGORIES
    }

    def projected_bytes_for_equal_count(target_count: int) -> int:
        return sum(
            max(0, target_count - global_category_counts.get(category, 0))
            * average_image_bytes[category]
            for category in CATEGORIES
        )

    # Find the highest shared image count supportable by the remaining
    # repository storage. This target grows automatically when all folders
    # reach the current common count.
    low = starting_global_max_count
    high = max(low + 1, 1)
    while projected_bytes_for_equal_count(high) <= usable_budget:
        low = high
        high = max(high + 1, high * 2)
    left, right = low, high
    while left < right:
        middle = (left + right + 1) // 2
        if projected_bytes_for_equal_count(middle) <= usable_budget:
            left = middle
        else:
            right = middle - 1
    target_category_count = left

    if target_category_count <= starting_global_max_count:
        print(json.dumps({
            "status": "repository_budget_reached",
            "git_object_bytes": start_size,
            "available_budget_bytes": available_budget,
            "safety_reserve_bytes": repository_safety_reserve,
            "equal_category_count": starting_global_max_count,
        }))
        return 0

    accepted: list[dict] = []
    added_bytes = 0
    download_attempts = 0
    search_pages = 0
    run_budget_hit = False
    rejected: dict[str, int] = {}
    failures: list[str] = []

    def reject(reason: str) -> None:
        rejected[reason] = rejected.get(reason, 0) + 1

    for category in ordered_categories:
        if (
            len(accepted) >= args.max_new_images
            or added_bytes >= MAX_DOWNLOAD_BYTES_PER_RUN
            or download_attempts >= MAX_DOWNLOAD_ATTEMPTS_PER_RUN
            or run_budget_hit
        ):
            break
        queries = CATEGORIES[category]
        current_category_count = global_category_counts.get(category, 0)
        category_remaining = max(0, target_category_count - current_category_count)
        if category_remaining == 0:
            reject("global_category_target_reached")
            continue
        category_add_limit = min(PER_CATEGORY_LIMIT, category_remaining)
        if folder_usage[category] >= category_budgets[category]:
            reject("category_budget_reached")
            continue
        state = search_state.get(category, {})
        if not isinstance(state, dict):
            state = {}
        query_index = int(state.get("query_index", 0)) % len(queries)
        offset = max(0, int(state.get("offset", 0)))
        if offset >= 500:
            query_index = (query_index + 1) % len(queries)
            offset = 0

        category_added = 0
        pages_processed = 0
        query_text = queries[query_index]
        while (
            category_added < category_add_limit
            and pages_processed < MAX_SEARCH_PAGES_PER_CATEGORY_PER_RUN
            and len(accepted) < args.max_new_images
            and download_attempts < MAX_DOWNLOAD_ATTEMPTS_PER_RUN
            and added_bytes < MAX_DOWNLOAD_BYTES_PER_RUN
            and not run_budget_hit
        ):
            query_text = queries[query_index]
            try:
                pages = fetch_search_page(query_text, offset)
            except Exception as exc:
                failures.append(f"{category}: search failed: {str(exc)[:200]}")
                pages_processed += 1
                search_pages += 1
                query_index = (query_index + 1) % len(queries)
                offset = 0
                time.sleep(1.1)
                continue

            pages_processed += 1
            search_pages += 1
            if not pages:
                query_index = (query_index + 1) % len(queries)
                offset = 0
                time.sleep(1.1)
                continue

            for page in pages:
                if (
                    len(accepted) >= args.max_new_images
                    or category_added >= category_add_limit
                    or download_attempts >= MAX_DOWNLOAD_ATTEMPTS_PER_RUN
                    or added_bytes >= MAX_DOWNLOAD_BYTES_PER_RUN
                    or run_budget_hit
                ):
                    break
                title = page.get("title")
                infos = page.get("imageinfo")
                if not isinstance(title, str) or not isinstance(infos, list) or not infos:
                    reject("missing_imageinfo")
                    continue
                if normalize_title(title) in existing_titles:
                    reject("already_published_title_in_any_volume")
                    continue
                info = infos[0]
                if not isinstance(info, dict):
                    reject("invalid_imageinfo")
                    continue
                mime = str(info.get("mime", "")).lower()
                suffix = MIME_SUFFIX.get(mime)
                if suffix is None:
                    reject("unsupported_mime")
                    continue
                width = info.get("width")
                height = info.get("height")
                size = info.get("size")
                if not (
                    isinstance(width, int) and isinstance(height, int)
                    and width >= 2560 and height >= 1440 and width > height
                ):
                    reject("metadata_dimensions")
                    continue
                if not isinstance(size, int) or size <= 0 or size > MAX_IMAGE_BYTES:
                    reject("metadata_file_size")
                    continue
                if folder_usage[category] + size > category_budgets[category]:
                    reject("category_budget_would_be_exceeded")
                    continue
                ext = info.get("extmetadata", {})
                if not isinstance(ext, dict):
                    reject("missing_license_metadata")
                    continue
                license_info = license_details(ext)
                if license_info is None:
                    reject("license_not_allowlisted")
                    continue
                license_name, license_url = license_info
                creator = clean(ext.get("Artist"))
                credit = clean(ext.get("Credit"))
                description = clean(ext.get("ImageDescription"))
                if not creator:
                    creator = credit
                if not creator:
                    reject("missing_creator_attribution")
                    continue
                image_url = info.get("url")
                if not isinstance(image_url, str):
                    reject("missing_original_url")
                    continue
                if image_url.startswith("http://"):
                    image_url = "https://" + image_url[len("http://"):]
                if not image_url.startswith("https://"):
                    reject("non_https_original_url")
                    continue

                download_attempts += 1
                try:
                    payload = image_bytes(image_url)
                    if len(payload) > MAX_DOWNLOAD_BYTES_PER_RUN - added_bytes:
                        reject("run_download_budget_reached")
                        run_budget_hit = True
                        break
                    real_width, real_height, colors = validate_image(payload, mime)
                except Exception as exc:
                    reject("download_or_validation_failed")
                    failures.append(f"{title}: {str(exc)[:200]}")
                    time.sleep(0.35)
                    continue
                if folder_usage[category] + len(payload) > category_budgets[category]:
                    reject("category_budget_would_be_exceeded")
                    continue
                if len(payload) > available_budget - added_bytes - repository_safety_reserve:
                    reject("repository_budget_reserve_would_be_exceeded")
                    run_budget_hit = True
                    break

                digest = hashlib.sha256(payload).hexdigest()
                if digest in existing_shas:
                    reject("duplicate_sha256")
                    continue
                filename = digest + suffix
                relative_path = Path("Fenrir Wallpapers") / category / filename
                destination = ROOT / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    reject("destination_exists")
                    continue
                destination.write_bytes(payload)

                artist_credit = credit or creator
                attribution = (
                    f"{artist_credit}. {title.removeprefix('File:')} "
                    f"via Wikimedia Commons. License: {license_name}."
                )
                accepted.append({
                    "path": relative_path.as_posix(),
                    "sha256": digest,
                    "file_size_bytes": len(payload),
                    "mime_type": mime,
                    "width": real_width,
                    "height": real_height,
                    "dominant_colors": colors,
                    "title": title.removeprefix("File:"),
                    "description": description,
                    "creator": creator,
                    "credit": artist_credit,
                    "attribution": attribution,
                    "source": "Wikimedia Commons",
                    "source_page": commons_page_url(title),
                    "original_file_url": image_url,
                    "license_identifier": license_name,
                    "license_url": license_url,
                    "license_review": "automated metadata gate; verify file page for corrections",
                    "publication_policy": "CC0/Public Domain/CC BY/CC BY-SA; NC and ND excluded",
                })
                existing_shas.add(digest)
                existing_titles.add(normalize_title(title))
                added_bytes += len(payload)
                folder_usage[category] += len(payload)
                category_added += 1
                global_category_counts[category] = global_category_counts.get(category, 0) + 1
                time.sleep(0.35)

            next_offset = offset + PAGE_SIZE
            if next_offset >= 500:
                query_index = (query_index + 1) % len(queries)
                offset = 0
            else:
                offset = next_offset
            time.sleep(1.1)

        search_state[category] = {
            "query_index": query_index,
            "offset": offset,
            "last_query": query_text,
            "last_run_images_added": category_added,
            "last_run_pages_scanned": pages_processed,
        }

    search_state["_category_start"] = (category_start + 1) % len(category_names)

    if accepted:
        index["items"].extend(accepted)
        index["items"].sort(key=lambda item: item.get("path", ""))
        index["count"] = len(index["items"])
        index["search_state"] = search_state
        index["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = INDEX_PATH.with_name(INDEX_PATH.name + ".tmp")
        temporary.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(INDEX_PATH)
    else:
        # Persist cursors to ensure subsequent scheduled runs move forward.
        index["search_state"] = search_state
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "status": "images_added" if accepted else "no_eligible_images_this_run",
        "new_images": len(accepted),
        "new_image_bytes": added_bytes,
        "total_manifest_images": len(index["items"]),
        "git_object_bytes_before": start_size,
        "repository_budget_bytes": MAX_REPOSITORY_BYTES,
        "category_budgets_bytes": category_budgets,
        "category_usage_bytes": folder_usage,
        "global_max_category_count_before": starting_global_max_count,
        "global_equal_count_capacity_target": target_category_count,
        "average_image_bytes_by_category": average_image_bytes,
        "projected_bytes_to_equal_count_target": projected_bytes_for_equal_count(target_category_count),
        "repository_safety_reserve_bytes": repository_safety_reserve,
        "global_category_counts_after": global_category_counts,
        "download_attempts": download_attempts,
        "search_pages": search_pages,
        "rejected": rejected,
        "source": "Wikimedia Commons",
        "failures": failures[:20],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Continue incremental Commons collection from the persisted manifest cursor.



# Continue incremental Volume 03 acquisition from the persisted cross-volume cursors.

# Continue Volume 03 batch after the previous verified image push.

# Continue incremental, library-wide unique wallpaper acquisition.

# Continue sequential Volume 03 acquisition toward the 8 GiB target.

# Continue Volume 03 population with the next cursor slice.

# Continue the next bounded Volume 03 source cursor batch.

# Continue the Volume 03 campaign with the next persisted Commons cursor slice.

# Continue Volume 03 collection after the previous committed batch.

# Continue next serialized Volume 03 acquisition slice toward storage target.

# Continue the sequential Volume 03 import campaign after the latest verified commit.

# Continue serialized image acquisition from the current Volume 03 cursors.

# Continue Volume 03 import toward the configured 8 GiB target.

# Continue next serialized Volume 03 batch toward its storage ceiling.

# Continue filling under-target folders within remaining repository capacity.

# Continue filling under-target folders within remaining Volume 03 capacity.

# Continue filling under-target folders using the remaining Volume 03 storage budget.

# Continue filling Nordic, Obsidian and Unsorted to their configured folder targets.

# Final near-capacity pass: continue least-filled folders until the 8 GiB guard stops imports.

# Volume 03 bootstrap: scheduled acquisition coordinator.
