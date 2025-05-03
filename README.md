# Immich Smart Albums

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Optional: Add build status, version badges etc. if you have them -->

Automatically create and update dynamic photo albums in your [Immich](https://immich.app/) instance based on powerful search criteria.

This Python utility uses Immich's native search capabilities (metadata and AI-powered smart search) along with optional custom local filters (JSONPath/regex) to keep your albums perfectly organized.

## Features

*   **Automated Album Management:** Define rules once, and the script keeps your albums updated.
*   **Leverage Immich Search:** Utilizes built-in metadata search (dates, locations, people) and AI smart search (objects, scenes, concepts).
*   **Fine-Grained Local Filtering:** Apply JSONPath and regex rules to asset metadata (camera model, filename, EXIF tags, etc.).
*   **Flexible Logic:** Combine multiple include and exclude rules using AND/OR logic.
*   **Non-Destructive:** Only *adds* assets to albums; never deletes assets or modifies existing album content (unless you re-run with different rules).
*   **Preview Mode:** See which assets *would* be added before committing.
*   **Automation Ready:** Easily run via cron or other schedulers.

## Getting Started

Let's get you up and running quickly!

### 1. Requirements

*   Python 3.6+
*   An Immich server instance
*   An Immich API Key

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/tahnau/immich-smart-albums.git
cd immich-smart-albums

# Install required Python packages
pip3 install requests jsonpath_ng
```

### 3. Configuration

The script needs your Immich server URL and an API key.

*   **Server URL:** The web address of your Immich instance (e.g., `https://immich.example.com`).
*   **API Key:** Generate one from your Immich User Settings -> API Keys.

You can provide these via environment variables (recommended) or command-line arguments:

```bash
# Recommended: Set Environment Variables
export IMMICH_SERVER_URL="https://your-immich.example.com"
export IMMICH_API_KEY="paste_your_long_api_key_here"

# Alternatively, use --server and --key flags in commands
```

### 4. Your First Run (Simple Examples)

It's best to start in **preview mode** (without the `--album` flag) to see what the script finds before adding anything to an album.

**Example 1: Preview Photos from Summer 2023**

First, create a simple filter file named `filters/summer-2023.json`:

```json
// filters/summer-2023.json
{
  "takenAfter": "2023-06-01T00:00:00.000Z",
  "takenBefore": "2023-08-31T23:59:59.999Z"
}
```

Now, run the script to *preview* the results:

```bash
python3 immich-smart-albums.py \
  --include-metadata-union filters/summer-2023.json \
  --verbose # Optional: Shows more detail
```

This command uses the Immich metadata search to find photos taken between June 1st and August 31st, 2023, and prints the matching asset IDs. No album is modified.

**Example 2: Add Beach Photos to an Album**

Create a filter file `filters/beach.json`:

```json
// filters/beach.json
{
  "query": "beach",
  "resultLimit": 200 // Good practice to limit smart search results
}
```

First, preview:

```bash
python3 immich-smart-albums.py \
  --include-smart-union filters/beach.json
```

If the preview looks good, find the **Album ID** for your target album. Go to the album in the Immich web UI, and copy the UUID from the URL (e.g., `.../albums/THIS_PART_IS_THE_ID`).

Now, run the command again, adding the `--album` flag:

```bash
# Replace YOUR_ALBUM_ID with the actual ID
python3 immich-smart-albums.py \
  --include-smart-union filters/beach.json \
  --album YOUR_ALBUM_ID
```

This command uses Immich's AI smart search to find photos matching "beach" and adds them to the specified album.

## How It Works (Conceptual Overview)

The script determines which assets to add to an album by following these steps:

1.  **Identify Potential Assets (Include Rules):**
    *   It fetches assets matching your `--include-*` rules. You can filter by:
        *   **Metadata:** Dates, locations, people, camera info (via `--include-metadata-*`).
        *   **Smart Search:** AI-based content recognition (via `--include-smart-*`).
        *   **Local Filters:** Custom JSONPath/regex rules on asset details (via `--include-local-filter-*`).
    *   Assets must match the combined criteria of *all* specified include categories (Metadata AND Smart AND Local). Within each category, you can use Union (OR logic) or Intersection (AND logic).

2.  **Remove Unwanted Assets (Exclude Rules):**
    *   It then removes any assets identified in step 1 that *also* match any of your `--exclude-*` rules.
    *   Exclusion works similarly, using Metadata, Smart, and Local filters. If an asset matches *any* exclude rule, it's removed (OR logic across categories).

3.  **Add to Album:**
    *   The remaining assets are added to the specified `--album` (if provided).

*(See the "Advanced Filtering Logic" section below for the precise technical details.)*

## More Examples

Here are examples demonstrating more complex filtering:

*(Assumes `IMMICH_SERVER_URL` and `IMMICH_API_KEY` are set as environment variables)*

**Example 3: Find Photos with Mountains AND Beach (Intersection)**

Create `filters/mountains.json` and `filters/beach.json` (as shown above).

```bash
# Uses smart search intersection: Must match BOTH queries
python3 immich-smart-albums.py \
  --include-smart-intersection filters/mountains.json filters/beach.json \
  --album mountain-beach-scenes-album-id
```

```json
// filters/mountains.json
{ "query": "mountains", "resultLimit": 100 }
```

**Example 4: Find Photos with Mountains OR Beach (Union)**

```bash
# Uses smart search union: Must match EITHER query
python3 immich-smart-albums.py \
  --include-smart-union filters/mountains.json filters/beach.json \
  --album mountain-or-beach-scenes-album-id
```

**Example 5: Exclude People from Mountain Photos**

Create `filters/people.json`.

```bash
# Include mountains, but exclude photos containing people
python3 immich-smart-albums.py \
  --include-smart-union filters/mountains.json \
  --exclude-smart-union filters/people.json \
  --album mountains-no-people-album-id
```

```json
// filters/people.json
{ "query": "person", "resultLimit": 500 } // Might need a higher limit for exclusion
```

**Example 6: Combine Filter Types (Beach Photos from Summer 2023)**

Uses the `filters/beach.json` and `filters/summer-2023.json` files from earlier examples.

```bash
# Assets must match BOTH the smart search ("beach") AND the metadata search (date range)
python3 immich-smart-albums.py \
  --include-smart-union filters/beach.json \
  --include-metadata-union filters/summer-2023.json \
  --album summer-beach-2023-album-id
```

**Example 7: Use Local Filters (iPhone Photos Only)**

Requires a metadata or smart search filter to be active first. Let's find all photos (using a wide date range as a proxy) and then filter locally for Apple devices.

Create `filters/all-time.json` and `filters/local-apple.json`.

```json
// filters/all-time.json
{ "takenAfter": "1970-01-01T00:00:00.000Z" } // Or adjust as needed
```

```json
// filters/local-apple.json
[
  {
    "path": "$.exifInfo.make",
    "regex": "Apple",
    "description": "Photos taken with any Apple device"
  }
]
```

```bash
python3 immich-smart-albums.py \
  --include-metadata-union filters/all-time.json \
  --include-local-filter-intersection filters/local-apple.json \
  --album apple-photos-album-id
```

## Understanding Filter Files (.json)

You define your search criteria in simple JSON files.

*   **Metadata Filters (`--*-metadata-*`)**: Use fields from the Immich `/search/metadata` API endpoint. Common fields: `takenAfter`, `takenBefore`, `city`, `state`, `country`, `make`, `model`, `personIds`.
    *   Example: `filters/summer-2023.json` (shown above)
    *   Example: Find photos with specific people: `{ "personIds": ["uuid-of-person1", "uuid-of-person2"] }`
*   **Smart Filters (`--*-smart-*`)**: Use fields from the Immich `/search` API endpoint (often called smart search). Key field: `query`. Always include `resultLimit`.
    *   Example: `filters/beach.json` (shown above)
*   **Local Filters (`--*-local-filter-*`)**: An array of JSONPath/regex rules applied *after* fetching assets via Metadata/Smart search. Each rule needs a `path` (using [JSONPath syntax](https://goessner.net/articles/JsonPath/)) and a `regex`.
    *   Example: `filters/local-apple.json` (shown above)
    *   Example: Find only `.JPG` files: `[{"path": "$.originalPath", "regex": "\\.jpe?g$", "description": "JPEG files only"}]`
    *   See the "Available Fields for Local Filters" section below for details on what data you can query.

## Command-Line Parameters

```
# Include parameters (OR logic within category)
--include-metadata-union <file1.json> [file2.json...]
--include-smart-union <file1.json> [file2.json...]
--include-local-filter-union <file1.json> [file2.json...]

# Include parameters (AND logic within category)
--include-metadata-intersection <file1.json> [file2.json...]
--include-smart-intersection <file1.json> [file2.json...]
--include-local-filter-intersection <file1.json> [file2.json...]

# Exclude parameters (Assets matching ANY listed file in UNION are flagged for exclusion)
--exclude-metadata-union <file1.json> [file2.json...]
--exclude-smart-union <file1.json> [file2.json...]
--exclude-local-filter-union <file1.json> [file2.json...]

# Exclude parameters (Assets matching ALL listed files in INTERSECTION are flagged for exclusion)
--exclude-metadata-intersection <file1.json> [file2.json...]
--exclude-smart-intersection <file1.json> [file2.json...]
--exclude-local-filter-intersection <file1.json> [file2.json...]

# Common parameters
--server      Immich server URL (or use IMMICH_SERVER_URL env var)
--key         Immich API Key (or use IMMICH_API_KEY env var)
--album       UUID of the target album (omit for preview mode)
--max-assets  Limit the total number of assets added in one run (optional)
--verbose     Enable detailed logging output
--help        Show help message with all options
```

## Advanced Filtering Logic

*(This section contains the detailed technical explanation of how filters are combined.)*

The script uses a precise order of operations to determine the final set of assets:

1.  **Calculate Initial Include Pool:**
    *   For each category (Metadata, Smart, Local) where `--include-*` flags are used:
        *   Calculate the result of `--include-*-union` filters (Union/OR logic).
        *   Calculate the result of `--include-*-intersection` filters (Intersection/AND logic).
        *   The category's result is the **intersection** of its Union result and its Intersection result. (If only one type of flag is used, the other defaults to `ALL` assets).
    *   If *no* include flags are used for an entire category, it defaults to `ALL` assets.
    *   The final `Include_Pool` is the **intersection** of the results from all three categories:
        `Include_Pool = Metadata_Result ∩ Smart_Result ∩ Local_Result`
    *   *Local Filter Dependency:* Local include filters are only evaluated if at least one Metadata or Smart include filter is also specified. Otherwise, `Local_Result` defaults to `ALL`.

2.  **Calculate Exclusion Pool:**
    *   For each category (Metadata, Smart, Local) where `--exclude-*` flags are used:
        *   Calculate the result of `--exclude-*-union` filters.
        *   Calculate the result of `--exclude-*-intersection` filters.
        *   The assets flagged for exclusion by this category are the **union** of its Union result and its Intersection result. (If a flag is omitted, its contribution is `∅` - empty set).
    *   The final `Exclude_Pool` is the **union** of the flagged assets from all three categories:
        `Exclude_Pool = Metadata_Exclude ∪ Smart_Exclude ∪ Local_Exclude`

3.  **Determine Final Asset Set:**
    *   The assets to be added to the album are those in the `Include_Pool` that are *not* in the `Exclude_Pool` (set difference):
        `Final Album Assets = Include_Pool − Exclude_Pool`

4.  **Apply Max Assets Limit:**
    *   If `--max-assets` is specified, the list is truncated to that size.

**Visual Representation:**

```
immich-smart-albums: Operation Tree

Legend:
  ∩ : Intersection (AND)
  ∪ : Union (OR)
  − : Set Difference (Subtract)
  ALL: Represents the set of all assets (used as a default).
  ∅ : Represents the empty set (used as a default).
  A.json, B.json, ... : Filter definition files.

───────────────────────────────────────────────────────────────────────────────
 INCLUDE Ruleset (Determines the initial asset pool via Intersection)
 Rule: An asset MUST satisfy the intersection (∩) of the results from ALL specified categories.
───────────────────────────────────────────────────────────────────────────────
  ├─ Metadata (Include) → Metadata_Result (Defaults to ALL if no flags used)
  ├─ Smart (Include)    → Smart_Result (Defaults to ALL if no flags used)
  └─ Local (Include)    → Local_Result (Defaults to ALL if no flags used OR dependency not met)

  ▸ Include_Pool = Metadata_Result ∩ Smart_Result ∩ Local_Result
───────────────────────────────────────────────────────────────────────────────
 EXCLUDE Ruleset (Removes assets from the initial pool via Union)
 Rule: An asset is REMOVED if it matches the union (∪) of ANY specific exclude condition.
───────────────────────────────────────────────────────────────────────────────
  ├─ Metadata (Exclude) → Metadata_Exclude (Defaults to ∅ if no flags used)
  ├─ Smart (Exclude)    → Smart_Exclude (Defaults to ∅ if no flags used)
  └─ Local (Exclude)    → Local_Exclude (Defaults to ∅ if no flags used)

  ▸ Exclude_Pool = Metadata_Exclude ∪ Smart_Exclude ∪ Local_Exclude
───────────────────────────────────────────────────────────────────────────────
 FINAL ASSET SET Calculation
───────────────────────────────────────────────────────────────────────────────
  Final Album Assets = Include_Pool − Exclude_Pool
  (Optional: Apply --max-assets limit)
───────────────────────────────────────────────────────────────────────────────
```

## Available Fields for Local Filters

Local filters (`--*-local-filter-*`) operate on the asset data fetched *after* the initial Metadata/Smart search. Here's an example structure of the data available for JSONPath queries:

```json
// Example Asset Data Structure for Local Filters
{
    "id": "53c77aa3-52ff-4819-8900-d7bf0b134752", // Asset UUID
    "deviceAssetId": "20250228_161739.JPG",       // Original ID from device
    "ownerId": "6f9cf9e4-c538-40c4-b18f-9663576679d5", // User UUID
    "deviceId": "Library Import",
    "libraryId": "f01b0af6-14e9-4dc0-9e78-4e6fb9181bae",
    "type": "IMAGE", // or VIDEO
    "originalPath": "/path/on/server/library/folder/file.jpg", // Full path in library
    "originalFileName": "file.jpg",
    "originalMimeType": "image/jpeg",
    "thumbhash": "...",
    "fileCreatedAt": "2025-02-28T14:17:39.402Z", // Filesystem creation time
    "fileModifiedAt": "2025-02-28T14:17:39.000Z", // Filesystem modification time
    "localDateTime": "2025-02-28T16:17:39.402Z", // Date taken (best guess by Immich)
    "updatedAt": "2025-03-03T00:00:32.609Z",   // Immich DB update time
    "isFavorite": false,
    "isArchived": false,
    "isTrashed": false,
    "duration": "0:00:00.00000", // For videos
    "exifInfo": { // May be null if no EXIF data
        "make": "Apple",
        "model": "iPhone 15 Pro",
        "exifImageWidth": 4032,
        "exifImageHeight": 3024,
        "fileSizeInByte": 1695013,
        "orientation": "1",
        "dateTimeOriginal": "2025-02-28T14:17:39.402+00:00", // Actual EXIF date
        "modifyDate": "2025-02-28T14:17:39+00:00",
        "timeZone": "UTC+2",
        "lensModel": "iPhone 15 Pro back triple camera 2.22mm f/2.2",
        "fNumber": 2.2,
        "focalLength": 2.22,
        "iso": 1600,
        "exposureTime": "1/34",
        "latitude": 60.1,
        "longitude": 24.1,
        "city": "Helsinki", // From GPS or reverse geocoding
        "state": "Uusimaa",
        "country": "Finland",
        "description": "",
        "projectionType": null, // For spherical panoramas
        "rating": null
    },
    "livePhotoVideoId": null, // UUID if it's a live photo
    "people": [], // IMPORTANT: This field is usually EMPTY here. Use Metadata search (`personIds`) to filter by people.
    "checksum": "...", // File checksum
    "isOffline": false,
    "hasMetadata": true,
    "duplicateId": null,
    "resized": true // Whether Immich has generated web/thumbnail versions
}
```

**Note:** The `people` array within this asset detail structure is typically empty in the data fetched by this script. To filter by people, use the `personIds` field within a **Metadata Filter** file (`--include-metadata-*` or `--exclude-metadata-*`).

## Important Notes & Tips

*   **Finding Album/Person IDs:** Get Album UUIDs from the URL when viewing an album. Get Person UUIDs from the URL when viewing a specific person's page (`/people/...`).
*   **Smart Search (`resultLimit`):** *Always* include `"resultLimit"` in your smart search filter JSON (e.g., `{ "query": "dog", "resultLimit": 200 }`). Without it, the API might return *all* assets sorted by relevance, which is slow and often includes irrelevant results. Be aware that if you ask for 200 results but only 10 truly match, the API might pad the results with less relevant items.
*   **Preview First:** Always run without `--album` first to check the results.
*   **Local Filter Dependency:** Remember that local filters (`--*-local-filter-*`) only process assets already fetched by a metadata or smart search filter in the same command. They cannot be the *only* filter type used.
*   **Performance:**
    *   Metadata searches are generally faster than smart searches.
    *   Use `resultLimit` in smart searches to reduce load.
    *   Use `--max-assets` to limit the final number added, especially during initial runs.
    *   Complex local filter regex can be slower than simpler Immich API searches.

## Use Cases

*   **Date-Based Albums:** Automatically create albums for specific years, quarters, or events (e.g., "Summer 2024", "Christmas 2023").
*   **People Albums:** Keep albums updated with photos of specific individuals or groups (e.g., "Kids", "Family Gatherings").
*   **Location Albums:** Collect photos taken in specific cities, states, or countries.
*   **Theme Albums:** Use smart search for albums like "Beach Trips", "Hiking Adventures", "Food Photos".
*   **Camera/Device Albums:** Create albums for photos taken with specific cameras or phones using local filters.
*   **Combined Criteria:** Find photos of specific people *at* a specific location or *during* a specific time period.
*   **Exclusion Use Case:** Create a "Best Of" album but exclude blurry photos (if Immich adds such a smart tag) or photos containing specific objects/people.

## Automation

You can easily run this script periodically using `cron` (Linux/macOS) or Task Scheduler (Windows).

Create a simple shell script (e.g., `update_albums.sh`):

```bash
#!/bin/bash

# Ensure script directory is current directory (adjust path if needed)
cd /path/to/immich-smart-albums

# Load environment variables if not already set globally
export IMMICH_SERVER_URL="https://your-immich.example.com"
export IMMICH_API_KEY="your_api_key"

echo "Starting Immich Smart Album update..."

# Example 1: Update Summer Beach Album
python3 immich-smart-albums.py \
  --include-smart-union filters/beach.json \
  --include-metadata-union filters/summer-dates.json \
  --album summer-beach-album-id \
  --verbose

# Example 2: Update Family Photos Album (excluding maybe work photos based on path)
# Create filters/local-exclude-work.json: [{"path": "$.originalPath", "regex": "/work-related-folder/"}]
python3 immich-smart-albums.py \
  --include-metadata-union filters/family-person-ids.json \
  --exclude-local-filter-union filters/local-exclude-work.json \
  --album family-album-id \
  --verbose

echo "Album update complete."

```

Make it executable (`chmod +x update_albums.sh`) and schedule it with `crontab -e`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

