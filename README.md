# Immich Smart Albums

This utility automates the updating of dynamic photo albums in your [Immich](https://immich.app/) instance. It combines Immich's powerful metadata and AI-powered smart search with advanced local filtering (JSONPath and regex) to precisely organize your photos.

**Use Cases:**
*   **Automated Sharing:** Automatically share photos of specific people from multiple Immich accounts into shared albums.
*   **Curated Public Albums:** Create "sanitized" albums for public viewing (e.g., family photos for relatives) by excluding sensitive content or specific individuals.
*   **Relationship Management:** Easily filter out photos where you and an "ex" appear together, ensuring your albums reflect current preferences.
*   **Advanced Organization:** Build highly specific albums based on criteria like camera model, ISO, file path, or any other EXIF/asset metadata.

## Getting Started: Building Your First Smart Album

Our first goal is to create an album for our friend, **Jane Doe**. We can easily do this by including her name:

```bash
python3 immich-smart-albums.py --include-person-names-union "Jane Doe" --album "Jane's Album"
```
(Note: If a person is not named in Immich, you can use their person ID (UUID). Similarly, you can refer to album UUIDs directly. Used names and UUIDs must exist.)

Now, let's expand our circle to include all our friends: **Jane Doe**, **John Smith**, and **Peter Pan**. We can simply add their names to the command to create a "Friends" album:

```bash
python3 immich-smart-albums.py --include-person-names-union "Jane Doe" "John Smith" "Peter Pan" --album "Friends"
```

But what if we want an album that *only* shows photos where **Jane Doe and John Smith are together**? For this, we use the `include-person-names-intersection` flag:

```bash
python3 immich-smart-albums.py --include-person-names-intersection "Jane Doe" "John Smith" --album "Jane and John Together"
```

Finally, to refine our "Friends" album, let's exclude any photos where John Smith appears with his ex, **Mary Poppins**. We can achieve this by combining our union of friends with an `exclude-person-names-intersection`:

```bash
python3 immich-smart-albums.py \
  --include-person-names-union "Jane Doe" "John Smith" "Peter Pan" \
  --exclude-person-names-intersection "John Smith" "Mary Poppins" \
  --album "Friends (No Exes)"
```
This demonstrates how you can precisely control who appears in your albums.

### Time-Traveling with Dates and Metadata

Beyond people, dates are crucial for organizing memories. Let's refine "Jane's Album" to only include photos taken **after 2020**. We can add a metadata filter directly to our command:

```bash
python3 immich-smart-albums.py \
  --include-person-names-union "Jane Doe" \
  --include-metadata-union '{"takenAfter": "2021-01-01T00:00:00.000Z"}' \
  --album "Jane's Album (Post 2020)"
```

We can also exclude specific periods. For instance, to exclude all photos from 2022 from Jane's album, we combine an `exclude-metadata-union` filter:

```bash
python3 immich-smart-albums.py \
  --include-person-names-union "Jane Doe" \
  --include-metadata-union '{"takenAfter": "2021-01-01T00:00:00.000Z"}' \
  --exclude-metadata-union '{"takenAfter": "2022-01-01T00:00:00.000Z", "takenBefore": "2022-12-31T23:59:59.999Z"}' \
  --album "Jane's Album (Post 2020, No 2022)"
```

For more complex or reusable date ranges, you can define them in a JSON file. For example, to create an album for "Summer 2025", first create `my_filters/summer-2025.json`:

```json
{
  "takenAfter": "2025-06-01T00:00:00.000Z",
  "takenBefore": "2025-08-31T23:59:59.999Z"
}
```
Then, run the script:
```bash
python3 immich-smart-albums.py --include-metadata-union my_filters/summer-2025.json --album "Summer 2025"
```

### Advanced Filtering with Local Filters

Sometimes, Immich's API doesn't expose all the properties we need for filtering. This is where **local filters** shine, allowing you to filter on asset data like `originalPath` using JSONPath and regular expressions. These filters are applied *after* the initial Immich API calls.

Let's say we want to ensure no work-related photos from `/photos/work_projects/` appear in Jane's personal album. First, define this filter in `my_filters/localfilter-no-work-photos.json`:

```json
[
  {"path": "$.originalPath", "regex": "^/photos/work_projects/.*"}
]
```
Then, integrate it into your command:

```bash
python3 immich-smart-albums.py \
  --include-person-names-union "Jane Doe" \
  --include-metadata-union '{"takenAfter": "2021-01-01T00:00:00.000Z"}' \
  --exclude-local-filter-union my_filters/localfilter-no-work-photos.json \
  --album "Jane's Album (No Work Photos)"
```
(Note: Local filters are applied to assets already selected by other API calls. If you want to filter an entire library by `originalPath`, you might need a broad initial filter like `metadata-all-photos.json` to fetch all assets first, which can be slow.)

### Intelligent Curation with Smart Search

Immich's AI-powered smart search allows for content-based filtering. Let's create an album of all photos that have **dogs** in them:

```bash
python3 immich-smart-albums.py --include-smart-union "dog" --album "Dogs"
```

Immich's smart search results are sorted by their match ratio. If you have many photos and want to retrieve a specific number of the most relevant "dog" photos, or if you have very few and want to ensure you get all available matches, you can adjust the number of items retrieved using the `@amount` filter. For example, to retrieve up to 500 "dog" photos:

```bash
python3 immich-smart-albums.py --include-smart-union "dog@500" --album "Dogs (Top 500)"
```

For the discerning dog lover, we might want to exclude any dog photos that *also* contain **cats** or **hamsters**:

```bash
python3 immich-smart-albums.py --include-smart-union "dog" --exclude-smart-union "cat" "hamster" --album "Dogs (No Cats. No Hamsters)"
```
(Smart search queries can also be provided via JSON files for more complex or reusable queries.)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tahnau/immich-smart-albums.git
    cd immich-smart-albums
    ```

2.  **Install dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

## Configuration

The script requires your Immich server URL and API key. These can be provided in one of three ways (in order of precedence):

1.  **Command-line arguments:** Use the `--server` and `--key` flags.
2.  **Environment variables:** Set the `IMMICH_SERVER_URL` and `IMMICH_API_KEY` environment variables.
3.  **.env file:** Create a `.env` file in the project root. You can copy the example file and edit it:
    ```bash
    cp .env.example .env
    ```
    Then, add your credentials to the `.env` file.

## Docker Usage

This project provides a `Dockerfile` and `docker-compose.yml` for running the `immich-smart-albums` utility in a containerized environment.

**Configuration:**
The Docker setup uses the `.env` file in the project root for `IMMICH_SERVER_URL` and `IMMICH_API_KEY`. **Note:** If `IMMICH_SERVER_URL` is hardcoded in `docker-compose.yml`, it will override the value in `.env`. When running inside Docker, `localhost` refers to the container, not your host. For `IMMICH_SERVER_URL`, consider using `http://host.docker.internal:2283` (for Docker Desktop) or your host machine's IP address.

**Commands:**
```bash
# Build the Docker image
docker compose build

# Run the application (prints user info, albums, and named faces by default)
docker compose run immich-smart-albums

# Run with filters and arguments (e.g., a smart filter)
docker compose run immich-smart-albums --include-smart-intersection my_filters/smart-dog.json

# Execute a custom script within the container
docker compose run immich-smart-albums bash -c "./my_custom_script.sh"

# Inspect logs
docker compose logs -f
```

## Usage

The main script is `immich-smart-albums.py`. It is highly configurable via command-line arguments.

**Recommended Workflow:**

1.  **Verify Connectivity (No Arguments):**
    It is highly recommended to first run the script without any arguments. This will attempt to connect to your Immich instance using the configured `IMMICH_SERVER_URL` and `IMMICH_API_KEY` (from `.env` or environment variables). A successful run will print your user profile details, album list, and named faces, confirming that your setup is correct and the application can access Immich.

    ```bash
    python3 immich-smart-albums.py
    ```
    (If using Docker: `docker compose run immich-smart-albums`)

2.  **Preview Mode (Simple Search):**
    Once connectivity is verified, you can start experimenting with filters in preview mode (by omitting the `--album` flag). This allows you to see which assets will be selected without modifying any albums. For example, to preview assets matching a smart search for "cat":

    ```bash
    python3 immich-smart-albums.py --include-smart-union "cat"
    ```

3.  **Adding to an Album (Persistence):**
    Once you are satisfied with the preview results, you can specify an album to add the assets to using the `--album` flag. Without the `--album` parameter, the script performs no persistent changes. When the `--album` parameter is used, the script will only add new items to the specified album.
    ```bash
    python3 immich-smart-albums.py --include-smart-union "cat" --album "My Cat Album"
    ```

### Advanced Usage

The `immich-smart-albums.py` script offers a comprehensive set of command-line arguments for fine-grained control over asset selection and album management.

#### General Options

*   `--album ALBUM`: Specifies the target album by ID (UUID) or name. If provided, matching assets will be added to this album. If omitted, the script runs in preview mode, displaying selected assets without making changes.
*   `--max-assets MAX_ASSETS`: Limits the total number of assets processed after all filters are applied. This affects both console output in preview mode and the number of assets added to an album. Note that selection is arbitrary as it operates on an unordered set.
*   `--default-smart-result-limit DEFAULT_SMART_RESULT_LIMIT`: Sets the default result limit for smart searches. Immich's smart search results are sorted by match ratio. This global setting defaults to 200 but can be overridden per query using the `@amount` notation (e.g., `'dog@500'`).
*   `--verbose`: Enables verbose output for detailed debugging information.

#### Filtering Arguments

The script supports various filtering mechanisms, each with `union` (OR logic) and `intersection` (AND logic) modes for both `include` and `exclude` operations. Arguments that accept a payload (e.g., `--include-metadata-union`, `--include-smart-union`) intelligently determine if the input is a file path (ending with `.json`) or a direct JSON string. For complex queries, you can often construct them using the Immich web UI's search functionality and then copy the resulting JSON payload from the browser's address bar into a `.json` file for reuse.

**1. Person Filters (by Name)**

These filters allow you to select or exclude assets based on the presence of specific individuals, identified by their names in Immich.

*   `--include-person-names-union NAME [NAME ...]`: Includes assets containing *any* of the specified person names.
*   `--include-person-names-intersection NAME [NAME ...]`: Includes assets containing *all* of the specified person names.
*   `--exclude-person-names-union NAME [NAME ...]`: Excludes assets containing *any* of the specified person names.
*   `--exclude-person-names-intersection NAME [NAME ...]`: Excludes assets containing *all* of the specified person names.

**2. Smart Search Filters**

Leverage Immich's AI-powered smart search to filter assets based on their content (e.g., objects, scenes).

*   `--include-smart-union QUERY [QUERY ...]`: Includes assets that match *any* of the specified smart search queries.
*   `--include-smart-intersection QUERY [QUERY ...]`: Includes assets that match *all* of the specified smart search queries.
*   `--exclude-smart-union QUERY [QUERY ...]`: Excludes assets that match *any* of the specified smart search queries.
*   `--exclude-smart-intersection QUERY [QUERY ...]`: Excludes assets that match *all* of the specified smart search queries.

**3. Metadata Filters**

Filter assets using Immich's rich metadata, such as dates, tags, or other properties.

*   `--include-metadata-union PAYLOAD [PAYLOAD ...]`: Includes assets that match *any* of the specified metadata filters.
*   `--include-metadata-intersection PAYLOAD [PAYLOAD ...]`: Includes assets that match *all* of the specified metadata filters.
*   `--exclude-metadata-union PAYLOAD [PAYLOAD ...]`: Excludes assets that match *any* of the specified metadata filters.
*   `--exclude-metadata-intersection PAYLOAD [PAYLOAD ...]`: Excludes assets that match *all* of the specified metadata filters.

**4. Local Filters (JSONPath and Regex)**

These filters are applied *after* initial Immich API calls, allowing for highly specific filtering on asset data using JSONPath expressions and regular expressions. This is useful for properties not directly exposed by Immich's search API, such as `originalPath`.

*   `--include-local-filter-union FILE_PATH [FILE_PATH ...]`: Includes assets that match *any* of the specified local filters.
*   `--include-local-filter-intersection FILE_PATH [FILE_PATH ...]`: Includes assets that match *all* of the specified local filters.
*   `--exclude-local-filter-union FILE_PATH [FILE_PATH ...]`: Excludes assets that match *any* of the specified local filters.
*   `--exclude-local-filter-intersection FILE_PATH [FILE_PATH ...]`: Excludes assets that match *all* of the specified local filters.

#### Performance Considerations

Each value provided to an `include` or `exclude` parameter (e.g., `--include-metadata-union "filter1.json" "filter2.json"`) results in a separate Immich API call. Each of these calls might involve loading multiple pages of assets. While Immich's search is generally efficient, for optimal performance, consider merging multiple search criteria into a single JSON search query whenever possible to reduce the number of API round trips.

For a complete list of arguments and their descriptions, run the script with the `--help` flag:
```bash
python3 immich-smart-albums.py --help
```


## Available Fields for Local Filters

Local filters (`--*-local-filter-*`) operate on the asset data fetched *after* the initial Metadata/Smart search. Here's an example structure of the data available for JSONPath queries:

```json
{
    "id": "53c77aa3-52ff-4819-8900-d7bf0b134752",
    "deviceAssetId": "20250228_161739.JPG",
    "ownerId": "6f9cf9e4-c538-40c4-b18f-9663576679d5",
    "deviceId": "Library Import",
    "libraryId": "f01b0af6-14e9-4dc0-9e78-4e6fb9181bae",
    "type": "IMAGE",
    "originalPath": "/path/on/server/library/folder/file.jpg",
    "originalFileName": "file.jpg",
    "originalMimeType": "image/jpeg",
    "thumbhash": "...",
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
        "focalLength": 2.22,
        "iso": 1600,
        "exposureTime": "1/34",
        "latitude": 60.1,
        "longitude": 24.1,
        "city": "Helsinki",
        "state": "Uusimaa",
        "country": "Finland",
        "description": "",
        "projectionType": null,
        "rating": null
    },
    "livePhotoVideoId": null,
    "people": [],
    "checksum": "...",
    "isOffline": false,
    "hasMetadata": true,
    "duplicateId": null,
    "resized": true
}
```


## Filter Examples

The `my_filters` directory contains a variety of example filters that you can use and adapt. Here are a few examples:

*   `metadata-favorites.json`: Selects all favorite photos.
*   `smart-vehicles.json`: Selects all photos that contain vehicles.
*   `localfilter-highiso.json`: Selects all photos with an ISO higher than 1600.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
