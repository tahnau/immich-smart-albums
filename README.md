# Immich Smart Albums

This utility empowers you to create dynamic photo albums in your [Immich](https://immich.app/) instance. It leverages Immich's search capabilities (both metadata and AI-powered smart search) and adds powerful local filtering to help you organize your photos exactly the way you want.

## The Story: Building the Perfect Album

Let's embark on a journey to create highly curated photo albums in Immich, starting simple and progressively adding more sophisticated filtering.

### Chapter 1: Curating by People – From Individuals to Groups

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

### Chapter 2: Time-Traveling with Dates and Metadata

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

For more complex or reusable date ranges, you can define them in a JSON file. For example, to create an album for "Summer 2025", first create `filters/summer-2025.json`:

```json
{
  "takenAfter": "2025-06-01T00:00:00.000Z",
  "takenBefore": "2025-08-31T23:59:59.999Z"
}
```
Then, run the script:
```bash
python3 immich-smart-albums.py --include-metadata-union filters/summer-2025.json --album "Summer 2025"
```

### Chapter 3: Advanced Filtering with Local Filters

Sometimes, Immich's API doesn't expose all the properties we need for filtering. This is where **local filters** shine, allowing you to filter on asset data like `originalPath` using JSONPath and regular expressions. These filters are applied *after* the initial Immich API calls.

Let's say we want to ensure no work-related photos from `/photos/work_projects/` appear in Jane's personal album. First, define this filter in `filters/localfilter-no-work-photos.json`:

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
  --exclude-local-filter-union filters/localfilter-no-work-photos.json \
  --album "Jane's Album (No Work Photos)"
```
(Note: Local filters are applied to assets already selected by other API calls. If you want to filter an entire library by `originalPath`, you might need a broad initial filter like `metadata-all-photos.json` to fetch all assets first, which can be slow.)

### Chapter 4: Intelligent Curation with Smart Search

Immich's AI-powered smart search allows for content-based filtering. Let's create an album of all photos that have **dogs** in them:

```bash
python3 immich-smart-albums.py --include-smart-union "dog" --album "Dogs"
```

Immich's smart search results are sorted by their match ratio. If you have many photos and want to retrieve a specific number of the most relevant "dog" photos, or if you have very few and want to ensure you get all available matches, you can adjust the number of items retrieved using the `@amount` filter. For example, to retrieve up to 500 "dog" photos:

```bash
python3 immich-smart-albums.py --include-smart-union "dog@500" --album "Dogs (Top 500)"
```

For the discerning dog lover, we might want to exclude any dog photos that *also* contain **cats**:

```bash
python3 immich-smart-albums.py --include-smart-union "dog" --exclude-smart-union "cat" --album "Dogs (No Cats)"
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

This project provides a `Dockerfile` and `docker-compose.yml` to easily run the `immich-smart-albums` utility in a containerized environment.

### Configuration for Docker

The Docker setup is designed to use the `.env` file located in the project root for your Immich server URL and API key.

**Important Note on `IMMICH_SERVER_URL`:**
When running inside Docker, `localhost` refers to the container itself, not your host machine. You have two primary options for configuring the Immich server address:

1.  **Overriding in `docker-compose.yml`:**
    You can explicitly set the `IMMICH_SERVER_URL` in `docker-compose.yml`. This will override any value set in `.env` for the container.

    To find your Docker host IP on Linux, you might use `ip addr show docker0` or `ifconfig docker0`.

2.  **Using `host.docker.internal` (Recommended for Docker Desktop):**
    Edit your project's `.env` file to set `IMMICH_SERVER_URL` to `http://host.docker.internal:2283` (or your Immich port). This special hostname resolves to your host machine's IP from within the Docker container.

### Running with Docker Compose

1.  **Build the Docker image:**
    ```bash
    docker compose build
    ```

2.  **Run the application:**
    The entire project folder is copied into the Docker environment, making `my_filters` configurations directly available.

    To run the application and print user profile details, album list, and named faces:
    ```bash
    docker compose run immich-smart-albums
    ```

3.  **Using filters and arguments:**
    Pass arguments to the script by appending them to the `docker compose run` command. For example, to use a smart filter:
    ```bash
    docker compose run immich-smart-albums --include-smart-intersection my_filters/smart-dog.json
    ```

### Running Custom Scripts

To execute custom shell scripts from the project root within the Docker container (e.g., `my_custom_script.sh`):
```bash
docker compose run immich-smart-albums bash -c "./my_custom_script.sh"
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

The script provides a wide range of options for filtering and combining assets.

**Note on Payload Handling:** For arguments that accept a payload (e.g., `--include-metadata-union`, `--include-smart-union`), the script intelligently determines if the input is a file path (ending with `.json`) or a direct JSON string. A convenient way to construct complex search queries is to use the Immich web UI's search functionality. The resulting JSON payload for your search query is often visible in the browser's address bar, which you can then copy and save as a `.json` file for use with this script.

Here are some of the key arguments:

*   `--include-metadata-union`: Include assets that match any of the specified metadata filters.
*   `--include-metadata-intersection`: Include assets that match all of the specified metadata filters.
*   `--exclude-metadata-union`: Exclude assets that match any of the specified metadata filters.
*   `--exclude-metadata-intersection`: Exclude assets that match all of the specified metadata filters.
*   `--include-smart-union`: Include assets that match any of the specified smart search queries.
*   `--include-smart-intersection`: Include assets that match all of the specified smart search queries.
*   `--exclude-smart-union`: Exclude assets that match any of the specified smart search queries.
*   `--exclude-smart-intersection`: Exclude assets that match all of the specified smart search queries.
*   `--include-person-ids-union`: Include assets that contain any of the specified person IDs.
*   `--include-person-ids-intersection`: Include assets that contain all of the specified person IDs.
*   `--exclude-person-ids-union`: Exclude assets that contain any of the specified person IDs.
*   `--exclude-person-ids-intersection`: Exclude assets that contain all of the specified person IDs.
*   `--include-local-filter-union`: Include assets that match any of the specified local filters (JSONPath and regex).
*   `--include-local-filter-intersection`: Include assets that match all of the specified local filters.
*   `--exclude-local-filter-union`: Exclude assets that match any of the specified local filters.
*   `--exclude-local-filter-intersection`: Exclude assets that match all of the specified local filters.

**Note on Smart Search Threshold:** Immich's smart search results are sorted by their match ratio and require a threshold to return results. You can specify this threshold using the `@amount` filter within your query (e.g., `"dog@200"` for a threshold of 200). The default threshold is typically 200 if not specified.

**Performance Note:** Each value provided to an `include` or `exclude` parameter (e.g., `--include-metadata-union "filter1.json" "filter2.json"`) results in a separate Immich API call. Each of these calls might involve loading multiple pages of assets. While Immich's search is generally efficient, for optimal performance, consider merging multiple search criteria into a single JSON search query whenever possible to reduce the number of API round trips.

For more details on the available arguments, run the script with the `--help` flag.


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


## Filter Examples

The `filters` directory contains a variety of example filters that you can use and adapt. Here are a few examples:

*   `metadata-favorites.json`: Selects all favorite photos.
*   `smart-vehicles.json`: Selects all photos that contain vehicles.
*   `localfilter-highiso.json`: Selects all photos with an ISO higher than 1600.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
