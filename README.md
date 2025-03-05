# Immich Smart Albums

A Python utility for creating and managing dynamic photo albums in Immich using native API searches and custom regex filters.

## Overview

Immich Smart Albums automates photo organization by adding matching images to albums based on search criteria. It:
- Uses Immich's native metadata and smart search APIs
- Applies local JSONPath and regex filters to image metadata
- Works non-destructively (only adds to albums, never deletes)
- Can run via crontab for daily maintenance

## Features

- Filter by date ranges, people, locations using metadata API
- Use natural language queries with smart search API (e.g., "beach sunset", "smiling children", "red car")
- Apply custom filters to any EXIF data (camera model, aperture, filepath and filename patterns, country, city)
- Combine multiple filters with inclusion/exclusion logic
- Find photos with specific combinations of people
- Combine person recognition with object detection (e.g., people with cars)

## Requirements

- Python 3
- An Immich server with API access

## Configuration

Generate API keys from your Immich portal:
```
immich.example.com/user-settings?isOpen=api-keys
```

Create a `secrets.sh` file:
```bash
export IMMICH_API_KEY_1="your-user1-api-key"
```

## Usage

Set environment variables:
```bash
export IMMICH_SERVER_URL="http://your-immich-server"
export IMMICH_API_KEY="your-api-key"
python3 immich-smart-albums.py [OPTIONS]
```

**Notes:** 
- Album IDs must be specified as UUIDs, which can be found in the URL bar when viewing an album in the Immich UI (e.g., `immich.example.com/albums/bb8ee34a-a22d-4bb9-aa67-d394353a06c0`)
- Person IDs can be found by clicking on a person's face in the UI, which reveals the UUID in the URL (e.g., `immich.example.com/people/8fbe472e-7463-4d97-ae2d-3efb3270e153`)
- Search queries can be extracted from the UI: Copy query string from URL after `/search?query=`, URL decode it
  - After decoding, the JSON works as-is as a filter file
  - Context searches in UI become smart search JSON files
  - Filename/metadata searches in UI become metadata search JSON files
- Local filtering requires metadata or smart search as well, as it filters those results and cannot run standalone
- Combining multiple search criteria in a single JSON query is much more efficient than using separate query files
- This is a hobby project originally created for personal use and generalized to be suitable for more general use cases

## Use Cases

### Date range albums
```bash
# summer-2023.json
{"takenAfter": "2023-06-01T00:00:00.000Z", "takenBefore": "2023-08-31T23:59:59.999Z"}

python3 immich-smart-albums.py --include-metadata-file filters/summer-2023.json --album summer-memories
```

### People together in Helsinki during specific period
```bash
# holidays-2022.json
{"personIds": ["person-id-1", "person-id-2"], "takenAfter": "2022-12-20T00:00:00.000Z", "takenBefore": "2023-01-10T23:59:59.999Z", "city":"Helsinki"}

python3 immich-smart-albums.py --include-metadata-file filters/holidays-2022.json --album holiday-together
```

### Camera model and file path filtering
```bash
# iphone8.json
[
  {"path": "$.exifInfo.make", "regex": "Apple"},
  {"path": "$.exifInfo.model", "regex": "iPhone 8"},
  {"path": "$.originalPath", "regex": "^/trip/2014-11-18", "description": "Files from trip with path starting with /trip/2014-11-18" } 
]

python3 immich-smart-albums.py --include-metadata-file all-images.json --include-local-filter-file filters/iphone8.json --album iphone8-photos
```


### People with objects
```bash
# people.json
{"personIds": ["your-id", "friend-id"], "query": "porsche car background", "resultLimit": 300}

python3 immich-smart-albums.py --include-metadata-file filters/people.json --album porsche-friends
```

## Crafting Filter JSON

### Resources
- [Immich API Documentation](https://immich.app/docs/api/search-smart/)

### Smart Search Tips
Always set `resultLimit` in smart-search as the API sorts by relevance and may return all images:
```json
{"query": "mountain", "resultLimit": 200}
```

### Filtering Logic

1. **Search Phase**: All includes are intersected (AND logic)
2. **Exclusion Phase**: Matching exclusions remove assets
3. **Local Filtering Phase**: JSONPath and regex filters applied
4. **Result Processing**: Optional limit, then display or add to album

Example filter combinations:
- `--include-metadata-file person1.json --include-metadata-file person2.json --include-smart-file beach.json`: Photos with both people at the beach
- `--include-metadata-file summer2023.json --exclude-smart-file nsfw.json`: Summer 2023 photos excluding NSFW content
- `--include-metadata-file family.json --include-local-filter-file canon-camera.json`: Family photos taken with Canon cameras

## Automation

Use `immich-smart-albums.sh` to automate album synchronization:
```bash
./immich-smart-albums.sh
```

## License

[MIT](LICENSE)
