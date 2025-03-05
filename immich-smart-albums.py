#!/usr/bin/env python3
import requests
import argparse
import json
import re
from functools import reduce
from jsonpath_ng import parse

def log(message, fg=None, verbose_only=True, verbose=False):
    """Centralized logging function"""
    if not verbose_only or verbose:
        if fg == "red":
            print(f"\033[91m{message}\033[0m")
        elif fg == "green":
            print(f"\033[92m{message}\033[0m")
        elif fg == "yellow":
            print(f"\033[93m{message}\033[0m")
        else:
            print(message)

def api_request(method, url, headers, params=None, json_data=None, verbose=False):
    """Centralized API request handler with error handling"""
    log(f"API {method} request to {url}", verbose_only=True, verbose=verbose)
    if params:
        log(f"Params: {params}", verbose_only=True, verbose=verbose)
    if json_data:
        log(f"Payload: {json_data}", verbose_only=True, verbose=verbose)

    try:
        if method.lower() == 'get':
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == 'post':
            response = requests.post(url, headers=headers, json=json_data)
        elif method.lower() == 'put':
            response = requests.put(url, headers=headers, json=json_data)
        else:
            log(f"Unsupported method: {method}", fg="red", verbose_only=False, verbose=verbose)
            return None

        log(f"Response status: {response.status_code}", verbose_only=True, verbose=verbose)
        log(f"Response: {response.text[:500]}..." if len(response.text) > 500 else f"Response: {response.text}",
            verbose_only=True, verbose=verbose)

        if not response.ok:
            log(f"API request failed: {response.status_code} - {response.text}", fg="red", verbose_only=False, verbose=verbose)
            return None

        return response.json() if response.text else None
    except requests.exceptions.RequestException as e:
        log(f"API request error: {str(e)}", fg="red", verbose_only=False, verbose=verbose)
        return None

def load_json_file(file_path, verbose=False):
    """Load and validate a JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        log(f"Successfully loaded JSON from {file_path}", verbose_only=True, verbose=verbose)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log(f"Error loading JSON file {file_path}: {str(e)}", fg="red", verbose_only=False, verbose=verbose)
        return None

def execute_search(server_url, api_key, query, search_type, verbose=False):
    """Execute a search using the Immich API with pagination support"""
    url = f"{server_url}/api/search/{search_type}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Check if user specified a result limit
    result_limit = None
    if query and "resultLimit" in query:
        result_limit = query["resultLimit"]
        log(f"Using result limit: {result_limit} for {search_type} search", verbose_only=True, verbose=verbose)

    all_assets = []
    page = 1
    size = 100  # Adjust as needed for performance

    while True:
        # Prepare query with pagination - always start with page 1
        payload = query.copy() if query else {}
        if "page" in payload:
            payload.pop("page")  # Remove any existing page parameter
        payload["page"] = page
        payload["size"] = size

        log(f"Executing {search_type} search (page {page})", verbose_only=True, verbose=verbose)
        result = api_request('post', url, headers, json_data=payload, verbose=verbose)

        if not result or "assets" not in result:
            log(f"Search returned no valid results on page {page}", fg="yellow", verbose_only=True, verbose=verbose)
            break

        # Extract assets from current page
        assets = result.get("assets", {}).get("items", [])
        all_assets.extend(assets)

        # Check if we've reached the result limit
        if result_limit and len(all_assets) >= result_limit:
            log(f"Reached result limit ({result_limit}), stopping search", verbose_only=True, verbose=verbose)
            all_assets = all_assets[:result_limit]  # Trim to exact limit
            break

        # Check if we have a next page
        next_page = result.get("assets", {}).get("nextPage")
        if next_page is None:
            log(f"Reached last page ({page}), total assets: {len(all_assets)}", verbose_only=True, verbose=verbose)
            break

        log(f"Retrieved {len(assets)} assets from page {page}", verbose_only=True, verbose=verbose)
        page += 1

    return all_assets

def apply_filters(assets, filters, is_include=True, verbose=False):
    """Apply JSONPath and regex filters to assets"""
    if not filters:
        # If no include filters, include all. If no exclude filters, exclude none.
        return {asset["id"] for asset in assets} if is_include else set()

    filtered_assets = set()
    filter_counts = {}  # Track count per filter

    for filter_item in filters:
        path = filter_item.get("path")
        regex = filter_item.get("regex")
        description = filter_item.get("description", f"{path}:{regex}")
        filter_counts[description] = 0

    for asset in assets:
        asset_id = asset["id"]
        match_all = True

        for filter_item in filters:
            path = filter_item.get("path")
            regex = filter_item.get("regex")
            description = filter_item.get("description", f"{path}:{regex}")

            try:
                jsonpath_expr = parse(path)
                matches = [match.value for match in jsonpath_expr.find(asset)]

                # For include filters, all must match; for exclude filters, any match excludes
                if matches:
                    if regex:
                        regex_match = any(re.search(regex, str(match), re.IGNORECASE) for match in matches)
                        if is_include and not regex_match:
                            match_all = False
                            log(f"Asset {asset_id} failed include filter: {description}", verbose_only=True, verbose=verbose)
                            break
                        elif not is_include and regex_match:
                            filtered_assets.add(asset_id)
                            filter_counts[description] += 1
                            log(f"Asset {asset_id} matched exclude filter: {description}", verbose_only=True, verbose=verbose)
                            break
                    elif not is_include:
                        # No regex but matches path, exclude it
                        filtered_assets.add(asset_id)
                        filter_counts[description] += 1
                        log(f"Asset {asset_id} matched exclude filter path: {path}", verbose_only=True, verbose=verbose)
                        break
                elif is_include:
                    # No matches for include filter
                    match_all = False
                    log(f"Asset {asset_id} failed include filter (no path matches): {path}", verbose_only=True, verbose=verbose)
                    break
            except Exception as e:
                log(f"JSONPath error for asset {asset_id} with expression '{path}': {str(e)}", fg="red", verbose_only=True, verbose=verbose)
                if is_include:
                    match_all = False
                    break

        # Add if all filters matched
        if is_include and match_all:
            filtered_assets.add(asset_id)
            for desc in filter_counts:
                filter_counts[desc] += 1
            log(f"Asset {asset_id} passed all include filters", verbose_only=True, verbose=verbose)

    # Log results per filter
    filter_type = "include" if is_include else "exclude"
    for desc, count in filter_counts.items():
        log(f"Filter '{desc}' ({filter_type}) matched {count} assets", verbose_only=False, verbose=verbose)

    return filtered_assets

def parse_filters(filter_files, filter_strings, verbose=False):
    """Load and parse filters from files and command-line strings"""
    filters = []

    # Load from files
    for file_path in filter_files or []:
        filter_data = load_json_file(file_path, verbose)
        if filter_data and isinstance(filter_data, list):
            filters.extend(filter_data)
            log(f"Loaded {len(filter_data)} filters from {file_path}", verbose_only=True, verbose=verbose)
        elif filter_data:
            log(f"Filter file {file_path} must contain a JSON array", fg="red", verbose_only=False, verbose=verbose)

    # Parse command-line filters
    for filter_str in filter_strings or []:
        parts = filter_str.split(':', 1)
        if len(parts) == 2:
            filters.append({"path": parts[0], "regex": parts[1]})
            log(f"Added filter from command line: {filter_str}", verbose_only=True, verbose=verbose)
        else:
            log(f"Invalid filter format: {filter_str}. Expected 'path:regex'", fg="yellow", verbose_only=False, verbose=verbose)

    return filters

def add_assets_to_album(server_url, api_key, album_id, asset_ids, chunk_size=500, verbose=False):
    """Add assets to an album in chunks"""
    url = f"{server_url}/api/albums/{album_id}/assets"
    headers = {"x-api-key": api_key, "Content-Type": "application/json", "Accept": "application/json"}

    total_added = 0
    asset_ids_list = list(asset_ids)

    # Process in chunks to avoid request size limits
    for i in range(0, len(asset_ids_list), chunk_size):
        chunk = asset_ids_list[i:i + chunk_size]
        payload = {"ids": chunk}

        log(f"Adding chunk of {len(chunk)} assets to album {album_id} ({i+1}-{i+len(chunk)} of {len(asset_ids_list)})",
            verbose_only=False, verbose=verbose)

        result = api_request('put', url, headers, json_data=payload, verbose=verbose)
        if result is not None:
            total_added += len(chunk)
            # Print URLs of assets added to album
            for asset_id in chunk:
                log(f"{server_url}/photos/{asset_id}", verbose_only=False, verbose=verbose)

    log(f"Added {total_added} of {len(asset_ids_list)} assets to album",
        fg="green" if total_added == len(asset_ids_list) else "yellow",
        verbose_only=False, verbose=verbose)

    return total_added

def main():
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Search Immich for photos using metadata and smart search APIs, apply JSONPath and regex filters, and optionally add to an album."
    )
    
    # Add arguments
    parser.add_argument("--key", help="Your Immich API Key (env: IMMICH_API_KEY)", default=None)
    parser.add_argument("--server", help="Your Immich server URL (env: IMMICH_SERVER_URL)", default=None)
    parser.add_argument("--album", help="ID of the album to add matching assets to (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging")
    parser.add_argument("--max-assets", type=int, help="Maximum number of assets to process", default=None)
    parser.add_argument("--include-metadata-file", nargs="+", type=str, 
                      help="Path to JSON file containing metadata search query (can specify multiple files)")
    parser.add_argument("--include-smart-file", nargs="+", type=str,
                      help="Path to JSON file containing smart search query (can specify multiple files)")
    parser.add_argument("--exclude-metadata-file", nargs="+", type=str,
                      help="Path to JSON file containing exclusion metadata search query (can specify multiple files)")
    parser.add_argument("--exclude-smart-file", nargs="+", type=str,
                      help="Path to JSON file containing exclusion smart search query (can specify multiple files)")
    parser.add_argument("--include-local-filter-file", nargs="+", type=str,
                      help="Path to JSON file containing local JSONPath and regex include filters (can specify multiple files)")
    parser.add_argument("--exclude-local-filter-file", nargs="+", type=str,
                      help="Path to JSON file containing local JSONPath and regex exclude filters (can specify multiple files)")

    # Parse arguments
    args = parser.parse_args()
    
    # Check for environment variables if not provided as arguments
    import os
    if not args.key:
        args.key = os.environ.get("IMMICH_API_KEY")
    if not args.server:
        args.server = os.environ.get("IMMICH_SERVER_URL")
    
    # Ensure required arguments are provided
    if not args.key or not args.server:
        log("Error: API key and server URL required.", fg="red", verbose_only=False, verbose=args.verbose)
        return 1

    # Check that include-local-filter-file is not used without include-metadata-file or include-smart-file
    if args.include_local_filter_file and not (args.include_metadata_file or args.include_smart_file):
        log("Error: --include-local-filter-file requires either --include-metadata-file or --include-smart-file to fetch data to filter.",
            fg="red", verbose_only=False, verbose=args.verbose)
        return 1

    # Remove trailing slash from server URL if present
    args.server = args.server.rstrip('/')

    # Initialize collections
    included_assets_by_search = []
    excluded_assets = set()
    unique_assets = {}
    all_assets = []

    # Step 1: Load and execute include searches
    def process_search_files(file_paths, search_type, is_include=True):
        """Process a list of search files with common code"""
        if not file_paths:
            return set()
            
        result_ids = set()
        for file_path in file_paths:
            query = load_json_file(file_path, args.verbose)
            if query is not None:  # Check that file was loaded successfully
                log(f"Executing {search_type} search from {file_path}", verbose_only=False, verbose=args.verbose)
                assets = execute_search(args.server, args.key, query, search_type, verbose=args.verbose)
                
                # Add assets to the global all_assets list
                all_assets.extend(assets)

                for asset in assets:
                    unique_assets[asset["id"]] = asset

                if is_include and assets:
                    asset_ids = {asset["id"] for asset in assets}
                    included_assets_by_search.append(asset_ids)
                    
                    # Calculate and show the impact on the final asset set
                    if len(included_assets_by_search) == 1:
                        current_set = asset_ids
                    else:
                        current_set = reduce(lambda x, y: x.intersection(y), included_assets_by_search)
                    
                    log(f"Found {len(assets)} assets matching {search_type} criteria in {file_path} (intersection now: {len(current_set)} assets)",
                        verbose_only=False, verbose=args.verbose)
                    
                elif not is_include:
                    result_ids.update({asset["id"] for asset in assets})
        return result_ids

    # Process include searches
    process_search_files(args.include_metadata_file, "metadata")
    process_search_files(args.include_smart_file, "smart")

    # Step 2: Calculate intersection of all include searches
    final_asset_ids = set()
    if included_assets_by_search:
        final_asset_ids = reduce(lambda x, y: x.intersection(y), included_assets_by_search)
        log(f"Intersection of all include searches: {len(final_asset_ids)} assets",
            verbose_only=False, verbose=args.verbose)

    # Step 3: Execute exclude searches
    original_count = len(final_asset_ids)
    
    # Track assets excluded by each file
    for file_path in args.exclude_metadata_file or []:
        query = load_json_file(file_path, args.verbose)
        if query is not None:
            log(f"Executing metadata exclusion search from {file_path}", verbose_only=False, verbose=args.verbose)
            assets = execute_search(args.server, args.key, query, "metadata", verbose=args.verbose)
            
            all_assets.extend(assets)
            
            excluded_ids = {asset["id"] for asset in assets}
            before_count = len(final_asset_ids)
            final_asset_ids -= excluded_ids
            excluded_count = before_count - len(final_asset_ids)
            
            log(f"Found {len(assets)} assets matching metadata exclusion criteria in {file_path} (excluded {excluded_count}, remaining: {len(final_asset_ids)})",
                verbose_only=False, verbose=args.verbose)
            
            # Track for later use
            excluded_assets.update(excluded_ids)
    
    for file_path in args.exclude_smart_file or []:
        query = load_json_file(file_path, args.verbose)
        if query is not None:
            log(f"Executing smart exclusion search from {file_path}", verbose_only=False, verbose=args.verbose)
            assets = execute_search(args.server, args.key, query, "smart", verbose=args.verbose)
            
            all_assets.extend(assets)
            
            excluded_ids = {asset["id"] for asset in assets}
            before_count = len(final_asset_ids)
            final_asset_ids -= excluded_ids
            excluded_count = before_count - len(final_asset_ids)
            
            log(f"Found {len(assets)} assets matching smart exclusion criteria in {file_path} (excluded {excluded_count}, remaining: {len(final_asset_ids)})",
                verbose_only=False, verbose=args.verbose)
            
            # Track for later use
            excluded_assets.update(excluded_ids)

    # Step 4: Remove excluded assets
    if final_asset_ids:
        final_asset_ids -= excluded_assets
        log(f"After applying exclusion searches: {len(final_asset_ids)} assets remaining",
            verbose_only=False, verbose=args.verbose)

    # Step 5: Parse and apply filters
    # First ensure unique_assets has all assets
    unique_assets_from_all = {}
    for asset in all_assets:
        unique_assets_from_all[asset["id"]] = asset

    log(f"Processing {len(unique_assets_from_all)} unique assets for filtering",
        verbose_only=True, verbose=args.verbose)

    # Load include filters
    include_filters = parse_filters(args.include_local_filter_file, [], args.verbose)
    log(f"Loaded {len(include_filters)} include filters", verbose_only=True, verbose=args.verbose)

    # Load exclude filters
    exclude_filters = parse_filters(args.exclude_local_filter_file, [], args.verbose)
    log(f"Loaded {len(exclude_filters)} exclude filters", verbose_only=True, verbose=args.verbose)

    # Apply include filters if specified
    if include_filters:
        # If we already have a set of assets from searches, filter them
        if final_asset_ids:
            # Only process assets that passed the search criteria
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids
                              if asset_id in unique_assets_from_all]
            include_filtered_ids = apply_filters(filtered_assets, include_filters,
                                                          is_include=True, verbose=args.verbose)
            final_asset_ids = include_filtered_ids
        else:
            # No previous filtering, apply to all assets
            include_filtered_ids = apply_filters(list(unique_assets_from_all.values()),
                                                         include_filters, is_include=True, verbose=args.verbose)
            final_asset_ids = include_filtered_ids

        log(f"After applying include filters: {len(final_asset_ids)} assets remaining",
            verbose_only=False, verbose=args.verbose)

    # Apply exclude filters if specified
    if exclude_filters:
        # Only process assets that are still included
        if final_asset_ids:
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids
                              if asset_id in unique_assets_from_all]
            exclude_filtered_ids = apply_filters(filtered_assets, exclude_filters,
                                                         is_include=False, verbose=args.verbose)
            final_asset_ids -= exclude_filtered_ids
        else:
            # Apply to all assets
            exclude_filtered_ids = apply_filters(list(unique_assets_from_all.values()),
                                                         exclude_filters, is_include=False, verbose=args.verbose)
            # Only exclude from assets we haven't already excluded
            if excluded_assets:
                final_asset_ids = {asset["id"] for asset in unique_assets_from_all.values()} - excluded_assets - exclude_filtered_ids
            else:
                final_asset_ids = {asset["id"] for asset in unique_assets_from_all.values()} - exclude_filtered_ids

        log(f"After applying exclude filters: {len(final_asset_ids)} assets remaining",
            verbose_only=False, verbose=args.verbose)

    # If we have no filters and no searches, include all assets
    if not final_asset_ids and not include_filters and not args.include_metadata_file and not args.include_smart_file:
        log("No include searches or filters specified. Including all non-excluded assets.",
            fg="yellow", verbose_only=False, verbose=args.verbose)
        final_asset_ids = {asset["id"] for asset in unique_assets_from_all.values()} - excluded_assets
        log(f"Total non-excluded assets: {len(final_asset_ids)}",
            verbose_only=False, verbose=args.verbose)

    # Step 6: Apply limit
    if final_asset_ids:
        # Apply limit if specified
        if args.max_assets and len(final_asset_ids) > args.max_assets:
            log(f"Limiting to {args.max_assets} assets (from {len(final_asset_ids)})", verbose_only=False, verbose=args.verbose)
            final_asset_ids = set(list(final_asset_ids)[:args.max_assets])

    # Step 7: Display results and add to album if requested
    if final_asset_ids:
        log(f"\nFinal assets selected: {len(final_asset_ids)}", verbose_only=False, verbose=args.verbose)

        if not args.album:
            # Just print asset URLs
            for asset_id in final_asset_ids:
                log(f"{args.server}/photos/{asset_id}", verbose_only=False, verbose=args.verbose)
        else:
            # Add to album
            add_assets_to_album(args.server, args.key, args.album, final_asset_ids, verbose=args.verbose)
    else:
        log("No assets matched all criteria.", fg="yellow", verbose_only=False, verbose=args.verbose)

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
