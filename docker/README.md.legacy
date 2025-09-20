# Immich Smart Albums - Docker

Docker container solution for running Immich Smart Albums. This container provides an easy way to run and manage the Immich Smart Albums tool in a containerized environment.

## Features

- 🐳 Easy deployment with Docker
- 🔒 Secure API key management
- 📁 Volume mounting for persistent configuration
- 🤖 Automated scheduling support
- 🔄 Automatic container updates

## Prerequisites

- Docker (version 20.10.0 or higher)
- Docker Compose (version 2.0.0 or higher)
- Immich server (with API access enabled)
- API key from your Immich instance

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/immich-app/immich-smart-albums.git
   cd immich-smart-albums
   ```

2. Create and configure the environment file:
   ```bash
   cd docker
   cp .env.example .env
   # Edit .env with your settings:
   # IMMICH_SERVER_URL=https://your-immich-server
   # IMMICH_API_KEY=your-api-key
   ```

3. Start the container:
   ```bash
   docker compose up -d
   ```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| IMMICH_SERVER_URL | URL of your Immich server | Yes | - |
| IMMICH_API_KEY | API key for authentication | Yes | - |

### Filter Configuration

Place your filter JSON files in the `config` directory. See the main [documentation](../README.md#filter-configuration) for filter format and options.

## Usage Examples

### Basic Usage

1. Preview matching photos:
   ```bash
   docker compose run --rm immich-smart-albums \
     --include-metadata-union /app/config/my-filter.json
   ```

2. Create or update an album:
   ```bash
   docker compose run --rm immich-smart-albums \
     --include-metadata-union /app/config/my-filter.json \
     --album my-album-name
   ```

### Advanced Usage

1. Combine multiple filters:
   ```bash
   docker compose run --rm immich-smart-albums \
     --include-metadata-union /app/config/filter1.json \
     --include-metadata-union /app/config/filter2.json \
     --album combined-album
   ```

2. Exclude specific photos:
   ```bash
   docker compose run --rm immich-smart-albums \
     --include-metadata-union /app/config/all-photos.json \
     --exclude-metadata-union /app/config/private.json \
     --album public-photos
   ```

## Directory Structure

```
docker/
├── config/                 # Your filter configuration files
├── .env                   # Environment configuration
├── docker-compose.yml     # Docker Compose configuration
└── Dockerfile            # Container build instructions
```

## Scheduling

To run the album updates on a schedule:

1. Using host cron:
   ```bash
   # Run daily at 2 AM
   0 2 * * * cd /path/to/immich-smart-albums/docker && docker compose run --rm immich-smart-albums --include-metadata-file /app/config/daily-update.json
   ```

2. Using container restart policy (as configured in docker-compose.yml):
   - The container will automatically restart and run the update process
   - Adjust the frequency using environment variables

## Troubleshooting

### Common Issues

1. Connection Issues
   - Verify your IMMICH_SERVER_URL is accessible
   - Check if your API key has the required permissions
   - Ensure your Docker network can reach the Immich server

2. Filter Problems
   - Validate JSON syntax in filter files
   - Check if date formats match YYYY-MM-DD
   - Verify that filter criteria are correctly formatted

### Logs

View container logs:
```bash
docker compose logs -f
```

## Security Considerations

- The API key is stored securely in the .env file
- The container runs with non-root user privileges
- Sensitive data is not exposed in logs
- Filter files are mounted read-only

## Support

- GitHub Issues: [Report a bug](https://github.com/immich-app/immich-smart-albums/issues)
- Documentation: [Wiki](https://github.com/immich-app/immich-smart-albums/wiki) 
