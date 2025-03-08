#!/usr/bin/env python3
import requests
import argparse
import json
import re
import os
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
    """Load and validate a JSON file or JSON string"""
    # If not a .json file, try parsing as JSON string first
    if not str(file_path).endswith('.json'):
        try:
            data = json.loads(file_path)
            log("Successfully parsed input as JSON string", verbose_only=True, verbose=verbose)
            return data
        except json.JSONDecodeError:
            # Not valid JSON string, try as file path instead
            pass
    # Handle as file path
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

def apply_filters(assets, filters, is_include=True, use_intersection=True, verbose=False):
    """Apply JSONPath and regex filters to assets with union or intersection mode"""
    if not filters:
        # If no include filters, include all. If no exclude filters, exclude none.
        return {asset["id"] for asset in assets} if is_include else set()

    filtered_assets = set()
    filter_counts = {}  # Track count per filter
    asset_matches = {asset["id"]: set() for asset in assets}  # Track which filters matched each asset

    for filter_item in filters:
        path = filter_item.get("path")
        regex = filter_item.get("regex")
        description = filter_item.get("description", f"{path}:{regex}")
        filter_counts[description] = 0

    # Process each asset against all filters
    for asset in assets:
        asset_id = asset["id"]
        matched_filters = set()

        for filter_item in filters:
            path = filter_item.get("path")
            regex = filter_item.get("regex")
            description = filter_item.get("description", f"{path}:{regex}")

            try:
                jsonpath_expr = parse(path)
                matches = [match.value for match in jsonpath_expr.find(asset)]

                if matches:
                    if regex:
                        regex_match = any(re.search(regex, str(match), re.IGNORECASE) for match in matches)
                        if regex_match:
                            matched_filters.add(description)
                            asset_matches[asset_id].add(description)
                            filter_counts[description] += 1
                            log(f"Asset {asset_id} matched filter: {description}", verbose_only=True, verbose=verbose)
                    else:
                        # No regex but matches path
                        matched_filters.add(description)
                        asset_matches[asset_id].add(description)
                        filter_counts[description] += 1
                        log(f"Asset {asset_id} matched path: {path}", verbose_only=True, verbose=verbose)
            except Exception as e:
                log(f"JSONPath error for asset {asset_id} with expression '{path}': {str(e)}", fg="red", verbose_only=True, verbose=verbose)

        # Determine if this asset should be included/excluded based on filter mode
        if is_include:
            if use_intersection:
                # For intersection mode, asset must match ALL filters
                if len(matched_filters) == len(filters):
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched ALL include filters (intersection mode)", verbose_only=True, verbose=verbose)
            else:
                # For union mode, asset must match ANY filter
                if matched_filters:
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched at least one include filter (union mode)", verbose_only=True, verbose=verbose)
        else:  # exclusion logic
            if use_intersection:
                # For intersection mode, asset must match ALL filters to be excluded
                if len(matched_filters) == len(filters):
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched ALL exclude filters (intersection mode)", verbose_only=True, verbose=verbose)
            else:
                # For union mode, asset must match ANY filter to be excluded
                if matched_filters:
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched at least one exclude filter (union mode)", verbose_only=True, verbose=verbose)

    # Log results per filter
    filter_type = "include" if is_include else "exclude"
    mode_type = "intersection" if use_intersection else "union"
    for desc, count in filter_counts.items():
        log(f"Filter '{desc}' ({filter_type}, {mode_type} mode) matched {count} assets", verbose_only=False, verbose=verbose)

    return filtered_assets

def parse_filters(filter_inputs, verbose=False):
    """Load and parse filters from file paths or raw JSON string values."""
    filters = []

    # Process file paths or raw JSON inputs
    for filter_input in filter_inputs or []:
        filter_data = None
        # Check if the input is a file path that exists
        if os.path.exists(filter_input):
            filter_data = load_json_file(filter_input, verbose)
            if filter_data and isinstance(filter_data, list):
                filters.extend(filter_data)
                log(f"Loaded {len(filter_data)} filters from file {filter_input}", verbose_only=True, verbose=verbose)
            elif filter_data:
                log(f"Filter file {filter_input} must contain a JSON array", fg="red", verbose_only=False, verbose=verbose)
        else:
            # Try to parse the input as a raw JSON string
            try:
                filter_data = json.loads(filter_input)
                if isinstance(filter_data, list):
                    filters.extend(filter_data)
                    log(f"Loaded {len(filter_data)} filters from raw JSON value", verbose_only=True, verbose=verbose)
                else:
                    log(f"Raw JSON input must be a JSON array, got {type(filter_data).__name__}", fg="red", verbose_only=False, verbose=verbose)
            except Exception as e:
                # If not a valid JSON string, check if it's a simple path:regex format
                parts = filter_input.split(':', 1)
                if len(parts) == 2:
                    filters.append({"path": parts[0], "regex": parts[1]})
                    log(f"Added filter from command line: {filter_input}", verbose_only=True, verbose=verbose)
                else:
                    log(f"Error parsing filter input {filter_input}: {e}", fg="red", verbose_only=False, verbose=verbose)

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

def execute_search_queries(server_url, api_key, query_files, search_type, verbose=False):
    """Execute multiple search queries and return all assets"""
    all_assets = []
    asset_sets = []
    
    if not query_files:
        return all_assets, asset_sets
        
    log(f"Processing {len(query_files)} {search_type} search files", verbose_only=False, verbose=verbose)
    
    for i, file_path in enumerate(query_files):
        log(f"Processing {search_type} file [{i+1}/{len(query_files)}]: {file_path}", verbose_only=False, verbose=verbose)
        
        query = load_json_file(file_path, verbose)
        if not query:
            log(f"Failed to load query from {file_path}", fg="red", verbose_only=False, verbose=verbose)
            continue
            
        assets = execute_search(server_url, api_key, query, search_type, verbose=verbose)
        
        if not assets:
            log(f"No assets found for {search_type} search in {file_path}", fg="yellow", verbose_only=False, verbose=verbose)
            continue
            
        # Store asset IDs for this search
        asset_ids = {asset["id"] for asset in assets}
        asset_sets.append(asset_ids)
        
        # Add to all assets
        all_assets.extend(assets)
        
        log(f"Found {len(assets)} assets matching {search_type} criteria in {file_path}",
            verbose_only=False, verbose=verbose)
            
    return all_assets, asset_sets

def calculate_combined_assets(asset_sets, mode="intersection"):
    """Calculate the combined asset set based on mode (union or intersection)"""
    if not asset_sets:
        return set()
        
    if len(asset_sets) == 1:
        return asset_sets[0]
        
    if mode == "intersection":
        # Return intersection of all sets
        return reduce(lambda x, y: x.intersection(y), asset_sets)
    else:  # union mode
        # Return union of all sets
        return reduce(lambda x, y: x.union(y), asset_sets)

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
    
    # New flexible search options
    # Smart search options
    parser.add_argument("--include-smart-union", nargs="+", type=str,
                      help="Path to one or more JSON files containing smart search queries (union mode)")
    parser.add_argument("--include-smart-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files containing smart search queries (intersection mode)")
    parser.add_argument("--exclude-smart-union", nargs="+", type=str,
                      help="Path to one or more JSON files containing exclusion smart search queries (union mode)")
    parser.add_argument("--exclude-smart-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files containing exclusion smart search queries (intersection mode)")
    
    # Metadata search options
    parser.add_argument("--include-metadata-union", nargs="+", type=str,
                      help="Path to one or more JSON files containing metadata search queries (union mode)")
    parser.add_argument("--include-metadata-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files containing metadata search queries (intersection mode)")
    parser.add_argument("--exclude-metadata-union", nargs="+", type=str,
                      help="Path to one or more JSON files containing exclusion metadata search queries (union mode)")
    parser.add_argument("--exclude-metadata-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files containing exclusion metadata search queries (intersection mode)")
    
    # Local filter options
    parser.add_argument("--include-local-filter-union", nargs="+", type=str,
                      help="Path to one or more JSON files or filter strings for local JSONPath and regex include filters (union mode)")
    parser.add_argument("--include-local-filter-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files or filter strings for local JSONPath and regex include filters (intersection mode)")
    parser.add_argument("--exclude-local-filter-union", nargs="+", type=str,
                      help="Path to one or more JSON files or filter strings for local JSONPath and regex exclude filters (union mode)")
    parser.add_argument("--exclude-local-filter-intersection", nargs="+", type=str,
                      help="Path to one or more JSON files or filter strings for local JSONPath and regex exclude filters (intersection mode)")
    


    # Parse arguments
    args = parser.parse_args()

    # Check for environment variables if not provided as arguments
    if not args.key:
        args.key = os.environ.get("IMMICH_API_KEY")
    if not args.server:
        args.server = os.environ.get("IMMICH_SERVER_URL")

    # Ensure required arguments are provided
    if not args.key:
        log("Error: API key is required. Set IMMICH_API_KEY environment variable or use --key parameter.",
            fg="red", verbose_only=False, verbose=args.verbose)
        return 1
    if not args.server:
        log("Error: Server URL is required. Set IMMICH_SERVER_URL environment variable or use --server parameter.",
            fg="red", verbose_only=False, verbose=args.verbose)
        return 1



    # Remove trailing slash from server URL if present
    args.server = args.server.rstrip('/')

    # Initialize collections
    all_assets = []
    unique_assets = {}
    final_asset_ids = set()

    # Step 1: Process include metadata search files (both intersection and union modes)
    metadata_union_assets, metadata_union_sets = execute_search_queries(
        args.server, args.key, args.include_metadata_union, "metadata", args.verbose)
    metadata_intersection_assets, metadata_intersection_sets = execute_search_queries(
        args.server, args.key, args.include_metadata_intersection, "metadata", args.verbose)
    
    # Add all assets to our collections
    all_assets.extend(metadata_union_assets)
    all_assets.extend(metadata_intersection_assets)
    
    # Calculate combined metadata assets based on modes
    metadata_union_result = calculate_combined_assets(metadata_union_sets, "union")
    metadata_intersection_result = calculate_combined_assets(metadata_intersection_sets, "intersection")
    
    if metadata_union_result and metadata_intersection_result:
        # If both modes are used for metadata, take the intersection of their results
        metadata_result = metadata_union_result.intersection(metadata_intersection_result)
        log(f"Combined metadata search result (union ∩ intersection): {len(metadata_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif metadata_union_result:
        metadata_result = metadata_union_result
        log(f"Metadata search union result: {len(metadata_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif metadata_intersection_result:
        metadata_result = metadata_intersection_result
        log(f"Metadata search intersection result: {len(metadata_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    else:
        metadata_result = set()

    # Step 2: Process include smart search files (both intersection and union modes)
    smart_union_assets, smart_union_sets = execute_search_queries(
        args.server, args.key, args.include_smart_union, "smart", args.verbose)
    smart_intersection_assets, smart_intersection_sets = execute_search_queries(
        args.server, args.key, args.include_smart_intersection, "smart", args.verbose)
    
    # Add all assets to our collections
    all_assets.extend(smart_union_assets)
    all_assets.extend(smart_intersection_assets)
    
    # Calculate combined smart assets based on modes
    smart_union_result = calculate_combined_assets(smart_union_sets, "union")
    smart_intersection_result = calculate_combined_assets(smart_intersection_sets, "intersection")
    
    if smart_union_result and smart_intersection_result:
        # If both modes are used for smart, take the intersection of their results
        smart_result = smart_union_result.intersection(smart_intersection_result)
        log(f"Combined smart search result (union ∩ intersection): {len(smart_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif smart_union_result:
        smart_result = smart_union_result
        log(f"Smart search union result: {len(smart_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif smart_intersection_result:
        smart_result = smart_intersection_result
        log(f"Smart search intersection result: {len(smart_result)} assets", 
            verbose_only=False, verbose=args.verbose)
    else:
        smart_result = set()

    # Step 3: Calculate intersection between metadata and smart results if both exist
    if metadata_result and smart_result:
        final_asset_ids = metadata_result.intersection(smart_result)
        log(f"Intersection between metadata and smart searches: {len(final_asset_ids)} assets",
            verbose_only=False, verbose=args.verbose)
    elif metadata_result:
        final_asset_ids = metadata_result
    elif smart_result:
        final_asset_ids = smart_result

    # Step 4: Execute exclude searches
    # Process exclude metadata union
    exclude_metadata_union_assets, exclude_metadata_union_sets = execute_search_queries(
        args.server, args.key, args.exclude_metadata_union, "metadata", args.verbose)
    exclude_metadata_union_result = calculate_combined_assets(exclude_metadata_union_sets, "union")
    
    # Process exclude metadata intersection
    exclude_metadata_intersection_assets, exclude_metadata_intersection_sets = execute_search_queries(
        args.server, args.key, args.exclude_metadata_intersection, "metadata", args.verbose)
    exclude_metadata_intersection_result = calculate_combined_assets(exclude_metadata_intersection_sets, "intersection")
    
    # Add exclude assets to all_assets for later filtering
    all_assets.extend(exclude_metadata_union_assets)
    all_assets.extend(exclude_metadata_intersection_assets)
    
    # Combine exclude metadata results
    exclude_metadata_result = exclude_metadata_union_result.union(exclude_metadata_intersection_result)
    
    # Process exclude smart union
    exclude_smart_union_assets, exclude_smart_union_sets = execute_search_queries(
        args.server, args.key, args.exclude_smart_union, "smart", args.verbose)
    exclude_smart_union_result = calculate_combined_assets(exclude_smart_union_sets, "union")
    
    # Process exclude smart intersection
    exclude_smart_intersection_assets, exclude_smart_intersection_sets = execute_search_queries(
        args.server, args.key, args.exclude_smart_intersection, "smart", args.verbose)
    exclude_smart_intersection_result = calculate_combined_assets(exclude_smart_intersection_sets, "intersection")
    
    # Add exclude assets to all_assets for later filtering
    all_assets.extend(exclude_smart_union_assets)
    all_assets.extend(exclude_smart_intersection_assets)
    
    # Combine exclude smart results
    exclude_smart_result = exclude_smart_union_result.union(exclude_smart_intersection_result)
    
    # Combine all exclude results
    exclude_result = exclude_metadata_result.union(exclude_smart_result)
    
    # Apply excludes if we have any
    if exclude_result:
        before_count = len(final_asset_ids)
        final_asset_ids -= exclude_result
        excluded_count = before_count - len(final_asset_ids)
        log(f"Excluded {excluded_count} assets from search results, remaining: {len(final_asset_ids)}",
            verbose_only=False, verbose=args.verbose)

    # Step 5: Ensure we have a master list of all unique assets
    unique_assets_from_all = {}
    for asset in all_assets:
        unique_assets_from_all[asset["id"]] = asset

    log(f"Processing {len(unique_assets_from_all)} unique assets for filtering",
        verbose_only=True, verbose=args.verbose)

    # Step 6: Parse and apply local filters
    # Load include filters (union mode)
    include_union_filters = parse_filters(args.include_local_filter_union, args.verbose)
    
    # Load include filters (intersection mode)
    include_intersection_filters = parse_filters(args.include_local_filter_intersection, args.verbose)
    
    # Load exclude filters (union mode)
    exclude_union_filters = parse_filters(args.exclude_local_filter_union, args.verbose)
    
    # Load exclude filters (intersection mode)
    exclude_intersection_filters = parse_filters(args.exclude_local_filter_intersection, args.verbose)
    
    log(f"Loaded {len(include_union_filters)} include union filters", verbose_only=False, verbose=args.verbose)
    log(f"Loaded {len(include_intersection_filters)} include intersection filters", verbose_only=False, verbose=args.verbose)
    log(f"Loaded {len(exclude_union_filters)} exclude union filters", verbose_only=False, verbose=args.verbose)
    log(f"Loaded {len(exclude_intersection_filters)} exclude intersection filters", verbose_only=False, verbose=args.verbose)

    # Apply include filters (union mode) if specified
    include_union_ids = set()
    if include_union_filters:
        if final_asset_ids:
            # Apply to assets that have passed searches
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids 
                              if asset_id in unique_assets_from_all]
            include_union_ids = apply_filters(filtered_assets, include_union_filters, 
                                            is_include=True, use_intersection=False, verbose=args.verbose)
        else:
            # No previous filtering, apply to all assets
            include_union_ids = apply_filters(list(unique_assets_from_all.values()),
                                            include_union_filters, is_include=True, 
                                            use_intersection=False, verbose=args.verbose)

    # Apply include filters (intersection mode) if specified
    include_intersection_ids = set()
    if include_intersection_filters:
        if final_asset_ids:
            # Apply to assets that have passed searches
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids 
                              if asset_id in unique_assets_from_all]
            include_intersection_ids = apply_filters(filtered_assets, include_intersection_filters, 
                                            is_include=True, use_intersection=True, verbose=args.verbose)
        else:
            # No previous filtering, apply to all assets
            include_intersection_ids = apply_filters(list(unique_assets_from_all.values()),
                                            include_intersection_filters, is_include=True, 
                                            use_intersection=True, verbose=args.verbose)

    # Combine include filter results if both types are specified
    if include_union_ids and include_intersection_ids:
        # Take the intersection of both results
        include_filter_ids = include_union_ids.intersection(include_intersection_ids)
        log(f"Combined include filter result (union ∩ intersection): {len(include_filter_ids)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif include_union_ids:
        include_filter_ids = include_union_ids
        log(f"Include filter union result: {len(include_filter_ids)} assets", 
            verbose_only=False, verbose=args.verbose)
    elif include_intersection_ids:
        include_filter_ids = include_intersection_ids
        log(f"Include filter intersection result: {len(include_filter_ids)} assets", 
            verbose_only=False, verbose=args.verbose)
    else:
        include_filter_ids = set()

    # Apply include filters to final asset set if we have them
    if include_filter_ids:
        if final_asset_ids:
            final_asset_ids = final_asset_ids.intersection(include_filter_ids)
        else:
            final_asset_ids = include_filter_ids
        log(f"After applying include filters: {len(final_asset_ids)} assets remaining",
            verbose_only=False, verbose=args.verbose)

    # Apply exclude filters (union mode)
    exclude_union_ids = set()
    if exclude_union_filters:
        if final_asset_ids:
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids
                              if asset_id in unique_assets_from_all]
            exclude_union_ids = apply_filters(filtered_assets, exclude_union_filters,
                                           is_include=False, use_intersection=False, verbose=args.verbose)
        else:
            exclude_union_ids = apply_filters(list(unique_assets_from_all.values()),
                                           exclude_union_filters, is_include=False,
                                           use_intersection=False, verbose=args.verbose)

    # Apply exclude filters (intersection mode)
    exclude_intersection_ids = set()
    if exclude_intersection_filters:
        if final_asset_ids:
            filtered_assets = [unique_assets_from_all[asset_id] for asset_id in final_asset_ids
                              if asset_id in unique_assets_from_all]
            exclude_intersection_ids = apply_filters(filtered_assets, exclude_intersection_filters,
                                                  is_include=False, use_intersection=True, verbose=args.verbose)
        else:
            exclude_intersection_ids = apply_filters(list(unique_assets_from_all.values()),
                                                  exclude_intersection_filters, is_include=False,
                                                  use_intersection=True, verbose=args.verbose)

    # Combine exclude filter results (union of both)
    exclude_filter_ids = exclude_union_ids.union(exclude_intersection_ids)
    
    # Apply exclude filters to final asset set
    if exclude_filter_ids:
        before_count = len(final_asset_ids)
        final_asset_ids -= exclude_filter_ids
        excluded_count = before_count - len(final_asset_ids)
        log(f"After applying exclude filters: excluded {excluded_count}, {len(final_asset_ids)} assets remaining",
            verbose_only=False, verbose=args.verbose)

    # If we have no filters and no searches, include all assets
    if not final_asset_ids and not include_union_filters and not include_intersection_filters and \
       not args.include_metadata_union and not args.include_metadata_intersection and \
       not args.include_smart_union and not args.include_smart_intersection:
        log("No include searches or filters specified. Including all non-excluded assets.",
            fg="yellow", verbose_only=False, verbose=args.verbose)
        final_asset_ids = {asset["id"] for asset in unique_assets_from_all.values()} - exclude_result - exclude_filter_ids
        log(f"Total non-excluded assets: {len(final_asset_ids)}",
            verbose_only=False, verbose=args.verbose)

    # Step 7: Apply limit
    if final_asset_ids and args.max_assets and len(final_asset_ids) > args.max_assets:
        log(f"Limiting to {args.max_assets} assets (from {len(final_asset_ids)})", 
            verbose_only=False, verbose=args.verbose)
        final_asset_ids = set(list(final_asset_ids)[:args.max_assets])

    # Step 8: Display results and add to album if requested
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
