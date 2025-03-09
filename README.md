# Immich Smart Albums

A Python utility for creating and managing dynamic photo albums in Immich using native API searches and custom regex filters.

## Overview

Immich Smart Albums automates photo organization by adding matching images to albums based on search criteria. It:
- Uses Immich's native metadata and smart search APIs
- Applies local JSONPath and regex filters to image metadata
- Works non-destructively (only adds to albums, never deletes or modifies)
- Can run via crontab for daily maintenance

## Requirements

- Python 3.6+
- Required packages: `requests`, `jsonpath-ng`
- An Immich server with API access

## Installation

```bash
# Clone repository
git clone https://github.com/tahnau/immich-smart-albums.git
cd immich-smart-albums

# Install dependencies
pip3 install requests jsonpath_ng
```

## Asset Filtering Architecture

The script implements a powerful and flexible asset filtering system with support for different search types and combination modes.

### Search Types

- **Metadata Search**: Searches assets based on their metadata (date, location, etc.)
- **Smart Search**: Uses AI-powered search for content-based matches
- **Local Filters**: Applies JSONPath and regex filters directly to asset data

### Filter Processing Overview

Imagine three include categories: **metadata**, **smart**, and **local filters**. For each category, you can provide a list of rule files as arguments. When rule files are supplied:

- **Union:** An asset qualifies if it meets **at least one** rule in the list.
- **Intersection:** An asset qualifies only if it meets **every** rule in the list.

These union/intersection operations are applied only when rule files are provided; if not, that category defaults to including all assets.

### Merging Process

1. **Final Include:**
   - Each used category (metadata, smart, local) processes its rule files (if any) using union/intersection logic.
   - The overall include set is the intersection of the category results:
     
     **Final Include = Metadata ∩ Smart ∩ Local**

2. **Final Exclude:**
   - Exclude arguments work similarly (accepting lists with union/intersection logic).
   - The overall exclude set is the union of these results:
     
     **Final Exclude = Exclude Union ∪ Exclude Intersection**

3. **Final Assets:**
   - The final asset set is determined by subtracting the exclude set from the include set:
     
     **Final Assets = Final Include – Final Exclude**

4. **Asset Limit:**
   - If an asset limit is set, the final list is trimmed accordingly.


### Command-Line Parameters

```
# Include parameters (union)
--include-metadata-union
--include-smart-union 
--include-local-filter-union

# Include parameters (intersection)
--include-metadata-intersection
--include-smart-intersection
--include-local-filter-intersection

# Exclude parameters (union)
--exclude-metadata-union
--exclude-smart-union
--exclude-local-filter-union

# Exclude parameters (intersection)
--exclude-metadata-intersection
--exclude-smart-intersection
--exclude-local-filter-intersection

# Common parameters
--key                     Your Immich API Key (env: IMMICH_API_KEY)
--server                  Your Immich server URL (env: IMMICH_SERVER_URL)
--album                   ID of the album to add matching assets to (optional)
--verbose                 Enable verbose output for debugging
--max-assets              Maximum number of assets to process
```

## Quick Start Examples

### Basic Usage - Preview Mode

Start by running the script without the `--album` parameter to preview results:

```bash
# Set environment variables
export IMMICH_SERVER_URL="https://your-immich-server"
export IMMICH_API_KEY="your-api-key"

# Preview summer photos from 2023
python3 immich-smart-albums.py --include-metadata-intersection filters/summer-2023.json
```

### Add Photos to an Album

Once satisfied with the preview, add the `--album` parameter:

```bash
# Add all beach photos to "Beach Memories" album
python3 immich-smart-albums.py --include-smart-union filters/beach.json --album beach-memories-album-id
```

### Boolean Search (AND)

Find assets with mountains AND beach (intersection mode):

```bash
python immich-smart-albums.py --key YOUR_API_KEY --server https://immich.example.com \
  --include-smart-intersection '{"query":"mountains", "resultLimit":100}' \
  '{"query":"beach", "resultLimit":100}'
```

### Boolean Search (OR)

Find assets with either mountains OR beach (union mode):

```bash
python immich-smart-albums.py --key YOUR_API_KEY --server https://immich.example.com \
  --include-smart-union '{"query":"mountains", "resultLimit":100}' \
  '{"query":"beach", "resultLimit":100}'
```

### Mixed Mode Example

When using both union and intersection modes together, the filtering becomes more powerful:

```bash
# This command finds:
# - Assets matching "mountains" OR "landscape" (union mode)
# - THAT ALSO match both "summer" AND "sunny" (intersection mode)
python immich-smart-albums.py --server https://immich.example.com --key YOUR_API_KEY \
  --include-smart-union '{"query":"mountains"}' '{"query":"landscape"}' \
  --include-smart-intersection '{"query":"summer"}' '{"query":"sunny"}'
```

The result will contain only assets that:
1. Match either "mountains" OR "landscape" (union condition)
2. AND ALSO match both "summer" AND "sunny" (intersection condition)

### Exclusion Filter

Find mountain scenes but exclude those with people:

```bash
python immich-smart-albums.py --key YOUR_API_KEY --server https://immich.example.com \
  --include-smart-union '{"query":"mountains", "resultLimit":100}' \
  --exclude-smart-union '{"query":"person", "resultLimit":100}'
```

### Complex Query

Find beach images taken in summer, but exclude those with people and sunsets:

```bash
python immich-smart-albums.py --key YOUR_API_KEY --server https://immich.example.com \
  --include-smart-union '{"query":"beach", "resultLimit":200}' \
  --include-metadata-union '{"datetime": {"from": "2023-06-01", "to": "2023-09-01"}}' \
  --exclude-smart-union '{"query":"person", "resultLimit":100}' '{"query":"sunset", "resultLimit":100}'
```

### Custom Local Filtering

Apply custom JSONPath filters to include only JPG images:

```bash
python immich-smart-albums.py --key YOUR_API_KEY --server https://immich.example.com \
  --include-smart-union '{"query":"mountains", "resultLimit":100}' \
  --include-local-filter-union '[{"path": "$.originalPath", "regex": "\\.jpe?g$", "description": "JPG files only"}]'
```

### Camera-Specific Albums using local filters

```bash
# Photos taken with Apple
python3 immich-smart-albums.py \
  --include-metadata-union filters/all-photos.json \
  --include-local-filter-intersection filters/localfilter-apple.json \
  --album apple-photos-album-id
```

## Configuration
Generate API keys from your Immich portal:
```
immich.example.com/user-settings?isOpen=api-keys
```

### Tips for Getting Started
- Album IDs must be specified as UUIDs, which can be found in the URL bar when viewing an album in the Immich UI (e.g., `immich.example.com/albums/bb8ee34a-a22d-4bb9-aa67-d394353a06c0`)
- Person IDs can be found by clicking on a person's face in the UI, which reveals the UUID in the URL (e.g., `immich.example.com/people/8fbe472e-7463-4d97-ae2d-3efb3270e153`)
- Search queries can be made and extracted from the UI: Copy query string from URL after `/search?query=`, URL decode it
  - After decoding, the JSON works as-is as a filter file
  - Context searches in UI become smart search JSON files
  - Filename/metadata searches in UI become metadata search JSON files

## Features

- Filter by date ranges, people, locations using metadata API
- Use natural language queries with smart search API (e.g., "beach sunset", "smiling children", "red car")
- Apply custom filters to any EXIF data (camera model, aperture, filepath and filename patterns, country, city)
- Combine multiple filters with inclusion/exclusion logic
- Find photos with specific combinations of people
- Combine person recognition with object detection (e.g., people with cars)

## Important Notes
- Smart search is not always "smart" - be aware of its limitations:
  - When using resultLimit, the API may return unrelated images after relevant matches
  - Example: If you search for "car" with resultLimit: 200 but only have 2 car photos, you'll get 198 unrelated images. Deal with it.
  - Use the preview mode (without --album) to check results before adding to albums
- Local filtering requires metadata or smart search as well - it cannot run standalone
- Combining multiple search criteria in a single JSON query is more efficient
- Always set `resultLimit` in smart-search as the API will otherwise return all Immich images sorted by relevance: ```json {"query": "mountain", "resultLimit": 200}```

## Advanced Local Filters

Local filters use JSONPath and regex to filter assets based on specific criteria. Example filter syntax:

```json
[
  {
    "path": "$.originalPath",
    "regex": "\\.jpe?g$",
    "description": "JPG files only"
  },
  {
    "path": "$.exifInfo.make",
    "regex": "Canon",
    "description": "Canon cameras only"
  }
]
```

In union mode, assets matching ANY filter are included. In intersection mode, assets must match ALL filters.

### Use Case: Apple photos taken in Finland
```bash
# filters/localfilter-apple.json
[ {"path": "$.exifInfo.make", "regex": "Apple", "description": "Photos taken with any Apple device"} ]

$ filters/localfilter-finland.json
[{"path": "$.exifInfo.country", "regex": "Finland", "description": "Photos taken in Finland"}]

python3 immich-smart-albums.py --include-metadata-union all-images.json --include-local-filter-intersection filters/localfilter-apple.json filters/localfilter-finland.json --album iphone-in-finland
```

## Performance Tips

1. Use `resultLimit` in search queries to limit initial result sets
2. Use `--max-assets` for final output limitation
3. Smart searches are more resource-intensive than metadata searches
4. For complex queries, prefer chaining multiple filters rather than complex regex

## Use Cases

### Date range albums
```bash
# 2023-Q1-memories
{ "takenAfter": "2023-01-01T00:00:00.000Z", "takenBefore": "2023-03-31T23:59:59.999Z" }

python3 immich-smart-albums.py --include-metadata-union filters/metadata-2023-Q1.json --album 2023-Q1-memories
```

### People together in Helsinki during specific period
```bash
# holidays-2022.json
{"personIds": ["person-id-1", "person-id-2"], "takenAfter": "2022-12-20T00:00:00.000Z", "takenBefore": "2023-01-10T23:59:59.999Z", "city":"Helsinki"}

python3 immich-smart-albums.py --include-metadata-union filters/holidays-2022.json --album holiday-together
```

### People with objects
```bash
# people.json
{"personIds": ["your-id", "friend-id"], "query": "porsche car background", "resultLimit": 300}

python3 immich-smart-albums.py --include-metadata-union filters/people.json --album porsche-friends
```

## Real-World Use Case
Originally created for a family setup with separate Immich accounts:

- Automatically collects photos of specific people from both accounts into a shared family album
- Creates a "safe for relatives" version by filtering out potential NSFW content
- Works alongside manual additions to the shared albums

## Crafting Filter JSON

### Resources
- [Immich API Documentation](https://immich.app/docs/api/search-smart/)

The following fields are available for local JSONPath and regex filters:
```json
{
                "id": "53c77aa3-52ff-4819-8900-d7bf0b134752",
                "deviceAssetId": "20250228_161739.JPG",
                "ownerId": "6f9cf9e4-c538-40c4-b18f-9663576679d5",
                "deviceId": "Library Import",
                "libraryId": "f01b0af6-14e9-4dc0-9e78-4e6fb9181bae",
                "type": "IMAGE",
                "originalPath": "/niitty/2025-02/20250228_161739.JPG",
                "originalFileName": "20250228_161739.JPG",
                "originalMimeType": "image/jpeg",
                "thumbhash": "3ygGDYI7hZacoIUuZ9dJiT1uoLoH",
                "fileCreatedAt": "2025-02-28T14:17:39.402Z",
                "fileModifiedAt": "2025-02-28T14:17:39.000Z",
                "localDateTime": "2025-02-28T16:17:39.402Z",
                "updatedAt": "2025-03-03T00:00:32.609Z",
                "isFavorite": false,
                "isArchived": false,
                "isTrashed": false,
                "duration": "0:00:00.00000",
                "exifInfo": {
                    "make": "Apple",
                    "model": "iPhone 15 Pro",
                    "exifImageWidth": 4032,
                    "exifImageHeight": 3024,
                    "fileSizeInByte": 1695013,
                    "orientation": "1",
                    "dateTimeOriginal": "2025-02-28T14:17:39.402+00:00",
                    "modifyDate": "2025-02-28T14:17:39+00:00",
                    "timeZone": "UTC+2",
                    "lensModel": "iPhone 15 Pro back triple camera 2.22mm f/2.2",
                    "fNumber": 2.2,
                    "focalLength": 2.220000029,
                    "iso": 1600,
                    "exposureTime": "1/34",
                    "latitude": 60.1000000,
                    "longitude": 24.100000000,
                    "city": "Helsinki",
                    "state": "Uusimaa",
                    "country": "Finland",
                    "description": "",
                    "projectionType": null,
                    "rating": null
                },
                "livePhotoVideoId": null,
                "people": [],
                "checksum": "mSPNjmXBvLCD6ukNAvUa0XAw+cg=",
                "isOffline": false,
                "hasMetadata": true,
                "duplicateId": null,
                "resized": true
            }
        ],
```
Note that the people field is always empty and cannot be used. The Immich search API does not bother to return all image details without loading the image separately.

## Automation

Create your own `immich-smart-albums.sh` to automate album synchronization:
```bash
#!/bin/bash
export IMMICH_SERVER_URL="http://your-immich-server"
export IMMICH_API_KEY="your-api-key"

# Daily family album update
python3 immich-smart-albums.py \
  --include-metadata-union filters/family.json \
  --exclude-smart-union filters/nsfw.json \
  --album family-album-uuid

# Weekly beach photos update
python3 immich-smart-albums.py \
  --include-smart-union filters/beach.json \
  --album beach-album-uuid

echo "Album synchronization complete!"
```

## License

[MIT](LICENSE)
