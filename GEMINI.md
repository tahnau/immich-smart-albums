# Immich Smart Albums

## Project Overview

This project provides a Python utility for automatically creating and updating dynamic photo albums in an [Immich](https://immich.app/) instance. It leverages Immich's native search capabilities (both metadata and AI-powered smart search) and allows for additional local filtering using JSONPath and regular expressions. This enables users to maintain highly organized photo albums based on a wide range of criteria.

The application is written in Python 3 and uses the `requests` library to interact with the Immich API. It is designed to be run from the command line and can be easily automated using cron or other scheduling mechanisms.

## Building and Running

### Prerequisites

*   Python 3.6+
*   An Immich server instance
*   An Immich API Key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tahnau/immich-smart-albums.git
    cd immich-smart-albums
    ```

2.  **Install dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

### Configuration

The script requires your Immich server URL and API key. These can be provided in one of three ways (in order of precedence):

1.  **Command-line arguments:** Use the `--server` and `--key` flags.
2.  **Environment variables:** Set the `IMMICH_SERVER_URL` and `IMMICH_API_KEY` environment variables.
3.  **.env file:** Create a `.env` file in the project root. You can copy the example file and edit it:
    ```bash
    cp .env.example .env
    ```
    Then, add your credentials to the `.env` file.

### Running the script

The main script is `immich-smart-albums.py`. It is highly configurable via command-line arguments.

**Preview Mode:**

It is recommended to first run the script in preview mode (by omitting the `--album` flag) to see which assets will be selected without modifying any albums.

```bash
python3 immich-smart-albums.py --include-metadata-union filters/summer-2023.json
```

**Adding to an album:**

Once you are satisfied with the preview, you can specify an album to add the assets to using the `--album` flag.

```bash
python3 immich-smart-albums.py --include-metadata-union filters/summer-2023.json --album <YOUR_ALBUM_ID_OR_NAME>
```

The `--album` flag can accept either an album ID (UUID) or an album name. Similarly, when filtering by people, you can use either the person's ID (UUID) or their name.

For more detailed examples and advanced usage, please refer to the `README.md` file.

## Development Conventions

*   **Code Style:** The project follows the standard PEP 8 style guide for Python code.
*   **Modularity:** The codebase is organized into modules within the `lib/` directory, promoting separation of concerns and maintainability.
    *   `api.py`: Handles all communication with the Immich API.
    *   `config.py`: Manages configuration from command-line arguments, environment variables, and the `.env` file.
    *   `filter.py`: Implements the local filtering logic using JSONPath and regex.
    *   `logger.py`: Provides a simple logging utility.
*   **Testing:** The project does not currently have a dedicated test suite. However, the `test.sh` script and `test_cases.txt` file suggest a manual testing process.
*   **Dependencies:** Python packages are managed using `pip` and the `requirements.txt` file.
*   **Automation:** The `backup.sh` script suggests a mechanism for backing up important files. The `docker/` directory provides resources for running the application in a containerized environment.
