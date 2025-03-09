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

### Combination Modes

Each search type supports two modes:

- **Union Mode**: Assets matching ANY of the queries are included (logical OR)
- **Intersection Mode**: Only assets matching ALL queries are included (logical AND)

### Filter Processing Order

Filters are applied in this sequence:

1. **Include Searches**: First metadata searches, then smart searches
2. **Exclude Searches**: Remove any excluded assets from the results
3. **Local Filters**: Apply additional JSONPath/regex filtering
4. **Asset Limit**: Apply any maximum asset limit

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

### Detailed Filtering Flow

1. **Include Searches**:
   - Execute metadata searches (both union and intersection)
   - Execute smart searches (both union and intersection)
   - For each type, calculate union and intersection results separately
   - When both union and intersection modes are used for the same search type (e.g., both `--include-smart-union` and `--include-smart-intersection`), the script takes the intersection of these two result sets
   - This means an asset must satisfy BOTH conditions: match at least one union query AND match all intersection queries
   - Intersect results from metadata and smart searches if both exist

2. **Exclude Searches**:
   - Execute metadata and smart exclude searches in both modes
   - Combine all excluded assets (union of all excludes)
   - Remove excluded assets from include results

3. **Local Filters**:
   - Apply include local filters (union and intersection)
   - Apply exclude local filters (union and intersection)
   - Combine and apply to search results

4. **Limit**:
   - If `--max-assets` is specified, limit the result set

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
# Photos taken with iPhone 15 Pro
python3 immich-smart-albums.py \
  --include-metadata-union filters/all-photos.json \
  --include-local-filter-intersection filters/iphone15pro.json \
  --album iphone15-photos-album-id
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

### Use Case: Camera model and file path filtering
```bash
# iphone8.json
[
  {"path": "$.exifInfo.make", "regex": "Apple"},
  {"path": "$.exifInfo.model", "regex": "iPhone 8"},
  {"path": "$.originalPath", "regex": "^/trip/2014-11-18", "description": "Files from trip with path starting with /trip/2014-11-18" } 
]

python3 immich-smart-albums.py --include-metadata-union all-images.json --include-local-filter-intersection filters/iphone8.json --album iphone8-photos
```

## Performance Tips

1. Use `resultLimit` in search queries to limit initial result sets
2. Use `--max-assets` for final output limitation
3. Smart searches are more resource-intensive than metadata searches
4. For complex queries, prefer chaining multiple filters rather than complex regex

## Use Cases

### Date range albums
```bash
# summer-2023.json
{"takenAfter": "2023-06-01T00:00:00.000Z", "takenBefore": "2023-08-31T23:59:59.999Z"}

python3 immich-smart-albums.py --include-metadata-union filters/summer-2023.json --album summer-memories
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
    "id": "1c71303d-9f8c-4cd3-bd27-1198a3b0cdb9",
    "deviceAssetId": "20250223_145925.JPG",
    "ownerId": "6f9cf9e4-c538-40c4-b18f-9663576679d5",
    "owner": {
        "id": "6f9cf9e4-c538-40c4-b18f-9663576679d5",
        "email": "person",
        "name": "person",
        "profileImagePath": "upload/profile/6f9cf9e4-c538-40c4-b18f-9663576679d5/99be9f8c-55d2-4dbe-8e55-f9499c316ca2.png",
        "avatarColor": "pink",
        "profileChangedAt": "2024-12-04T19:12:07.477+00:00"
    },
    "deviceId": "Library Import",
    "libraryId": "f01b0af6-14e9-4dc0-9e78-4e6fb9181bae",
    "type": "IMAGE",
    "originalPath": "/images/2025-02/20250223_145925.JPG",
    "originalFileName": "20250223_145925.JPG",
    "originalMimeType": "image/jpeg",
    "thumbhash": "khgKFQJfVKBYlnaYhXiIh6egqQup",
    "fileCreatedAt": "2025-02-23T12:59:25.861Z",
    "fileModifiedAt": "2025-02-23T12:59:25.000Z",
    "localDateTime": "2025-02-23T14:59:25.861Z",
    "updatedAt": "2025-02-26T00:00:41.736Z",
    "isFavorite": false,
    "isArchived": false,
    "isTrashed": false,
    "duration": "0:00:00.00000",
    "exifInfo": {
        "make": "Apple",
        "model": "iPhone 15 Pro",
        "exifImageWidth": 5712,
        "exifImageHeight": 4284,
        "fileSizeInByte": 4301831,
        "orientation": "6",
        "dateTimeOriginal": "2025-02-23T12:59:25.861+00:00",
        "modifyDate": "2025-02-23T12:59:25+00:00",
        "timeZone": "UTC+2",
        "lensModel": "iPhone 14 Pro back triple camera 6.765mm f/1.78",
        "fNumber": 1.8,
        "focalLength": 6.764999866,
        "iso": 800,
        "exposureTime": "1/60",
        "latitude": 60.20000000000,
        "longitude": 24.20000000000,
        "city": "Helsinki",
        "state": "Uusimaa",
        "country": "Finland",
        "description": "",
        "projectionType": null,
        "rating": null
    },
    "livePhotoVideoId": null,
    "tags": [],
    "people": [
        {
            "id": "60e5f100-ef96-42e9-9cc7-cc865c0639d6",
            "name": "person1",
            "birthDate": null,
            "thumbnailPath": "upload/thumbs/6f9cf9e4-c538-40c4-b18f-9663576679d5/60/e5/60e5f100-ef96-42e9-9cc7-cc865c0639d6.jpeg",
            "isHidden": false,
            "isFavorite": false,
            "updatedAt": "2024-12-04T16:42:47.144284+00:00",
            "faces": [
                {
                    "id": "8c24eccc-a59b-4e9f-9a0f-6c46b98b8155",
                    "imageHeight": 1920,
                    "imageWidth": 1440,
                    "boundingBoxX1": 250,
                    "boundingBoxX2": 580,
                    "boundingBoxY1": 364,
                    "boundingBoxY2": 785,
                    "sourceType": "machine-learning"
                }
            ]
        }
    ],
    "unassignedFaces": [],
    "checksum": "VPBFOP4sPPMUluPEts71v6wP+nM=",
    "stack": null,
    "isOffline": false,
    "hasMetadata": true,
    "duplicateId": null,
    "resized": true
}
```

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
