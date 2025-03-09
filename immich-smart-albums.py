#!/usr/bin/env python3
import requests
import argparse
import json
import re
import os
import sys
from functools import reduce
from jsonpath_ng import parse

def compute_merged(node, indent=0):
    """
    Recursively computes the merged set of asset IDs for a node and logs statistics with indentation.
    
    Modes:
      - "union": Union of children (or union of all sets in 'results' if leaf).
      - "intersection": Intersection of children (or intersection of all sets in 'results' if leaf).
      - "minus": Subtract the merged set of the second child from the first child's merged set.
    
    This version prints an "Entering" message before recursing into children,
    then logs the results of merging after processing them.
    
    Parameters:
      node (dict): Current node.
      indent (int): Indentation level for logging.
    
    Returns:
      set: Merged asset IDs.
    """
    prefix = "    " * indent  # 4 spaces per indent level

    if "children" in node and node["children"]:
        # Log entering the node
        print(f"{prefix}[MERGE - NODE] Entering node with mode '{node['mode']}' having {len(node['children'])} children")
        
        # Compute merged set for each child.
        child_results = []
        for child in node["children"]:
            res = compute_merged(child, indent=indent+1)
            child_results.append(res)
        
        child_counts = [len(r) for r in child_results]
        print(f"{prefix}[MERGE - NODE] About to merge children with counts: {child_counts}")
        
        # Merge children based on the node's mode.
        if node["mode"] == "union":
            merged = set.union(*child_results) if child_results else set()
            op = "Union"
        elif node["mode"] == "intersection":
            merged = set.intersection(*child_results) if child_results else set()
            op = "Intersection"
        elif node["mode"] == "minus":
            if len(child_results) != 2:
                raise ValueError("Minus node must have exactly two children (include and exclude)")
            merged = child_results[0] - child_results[1]
            op = "Minus (Subtract)"
        else:
            raise ValueError(f"Unknown mode: {node['mode']}")
        
        print(f"{prefix}[MERGE - NODE] {op} result: {len(merged)} items")
        node["merged"] = merged
        return merged

    elif "results" in node and node["results"]:
        # Log entering leaf node.
        keys = list(node["results"].keys())
        print(f"{prefix}[MERGE - LEAF] Entering leaf node with mode '{node['mode']}'. Query keys: {keys}")
        
        result_counts = {}
        result_sets = []
        for key, res in node["results"].items():
            res_set = set(res)
            result_sets.append(res_set)
            result_counts[key] = len(res_set)
        
        print(f"{prefix}[MERGE - LEAF] Raw query counts: {result_counts}")
        
        # Merge based on the node's mode.
        if node["mode"] == "union":
            merged = set.union(*result_sets) if result_sets else set()
            op = "Union"
        elif node["mode"] == "intersection":
            merged = set.intersection(*result_sets) if result_sets else set()
            op = "Intersection"
        else:
            merged = set()
            op = "Unknown"
        
        print(f"{prefix}[MERGE - LEAF] {op} result: {len(merged)} items")
        node["merged"] = merged
        return merged

    else:
        print(f"{prefix}[MERGE] Node empty. Merged count: 0")
        node["merged"] = set()
        return set()


#################################
# HELPER FUNCTIONS
#################################
def log(message, fg=None, verbose_only=True, verbose=False):
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
        text = response.text if len(response.text) <= 4500 else response.text[:4500] + "..."
        log(f"Response: {text}", verbose_only=True, verbose=verbose)
        if not response.ok:
            log(f"API request failed: {response.status_code} - {response.text}", fg="red", verbose_only=False, verbose=verbose)
            return None
        return response.json() if response.text else None
    except requests.exceptions.RequestException as e:
        log(f"API request error: {str(e)}", fg="red", verbose_only=False, verbose=verbose)
        return None

def load_json_file(file_path, verbose=False):
    if not str(file_path).endswith('.json'):
        try:
            data = json.loads(file_path)
            log("Successfully parsed input as JSON string", verbose_only=True, verbose=verbose)
            return data
        except json.JSONDecodeError:
            pass
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        log(f"Successfully loaded JSON from {file_path}", verbose_only=True, verbose=verbose)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log(f"Error loading JSON file {file_path}: {str(e)}", fg="red", verbose_only=False, verbose=verbose)
        return None

def execute_search(server_url, api_key, query, search_type, verbose=False):
    url = f"{server_url}/api/search/{search_type}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    result_limit = query.get("resultLimit") if query and "resultLimit" in query else None
    if result_limit:
        log(f"Using result limit: {result_limit} for {search_type} search", verbose_only=True, verbose=verbose)
    all_assets = []
    page = 1
    size = 100
    while True:
        payload = query.copy() if query else {}
        payload.pop("page", None)
        payload["page"] = page
        payload["withExif"] = True
        payload["size"] = size
        log(f"Executing {search_type} search (page {page})", verbose_only=True, verbose=verbose)
        result = api_request('post', url, headers, json_data=payload, verbose=verbose)
        if not result or "assets" not in result:
            log(f"Search returned no valid results on page {page}", fg="yellow", verbose_only=True, verbose=verbose)
            break
        assets = result.get("assets", {}).get("items", [])
        all_assets.extend(assets)
        if result_limit and len(all_assets) >= result_limit:
            log(f"Reached result limit ({result_limit}), stopping search", verbose_only=True, verbose=verbose)
            all_assets = all_assets[:result_limit]
            break
        if result.get("assets", {}).get("nextPage") is None:
            log(f"Reached last page ({page}), total assets: {len(all_assets)}", verbose_only=True, verbose=verbose)
            break
        log(f"Retrieved {len(assets)} assets from page {page}", verbose_only=True, verbose=verbose)
        page += 1
    return all_assets

def apply_filters(assets, filters, is_include=True, use_intersection=True, verbose=False):
    if not filters:
        return {asset["id"] for asset in assets} if is_include else set()
    filtered_assets = set()
    filter_counts = {}
    asset_matches = {asset["id"]: set() for asset in assets}
    for f in filters:
        path = f.get("path")
        regex = f.get("regex")
        description = f.get("description", f"{path}:{regex}")
        filter_counts[description] = 0
    for asset in assets:
        asset_id = asset["id"]
        matched_filters = set()
        for f in filters:
            path = f.get("path")
            regex = f.get("regex")
            description = f.get("description", f"{path}:{regex}")
            try:
                jsonpath_expr = parse(path)
                matches = [match.value for match in jsonpath_expr.find(asset)]
                if matches:
                    if regex:
                        if any(match is not None and re.search(regex, str(match), re.IGNORECASE) for match in matches):
                            matched_filters.add(description)
                            asset_matches[asset_id].add(description)
                            filter_counts[description] += 1
                            log(f"Asset {asset_id} matched filter: {description}", verbose_only=True, verbose=verbose)
                    else:
                        matched_filters.add(description)
                        asset_matches[asset_id].add(description)
                        filter_counts[description] += 1
                        log(f"Asset {asset_id} matched path: {path}", verbose_only=True, verbose=verbose)
            except Exception as e:
                log(f"JSONPath error for asset {asset_id} with expression '{path}': {str(e)}", fg="red", verbose_only=True, verbose=verbose)
        if is_include:
            if use_intersection:
                if len(matched_filters) == len(filters):
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched ALL include filters (intersection mode)", verbose_only=True, verbose=verbose)
            else:
                if matched_filters:
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched at least one include filter (union mode)", verbose_only=True, verbose=verbose)
        else:
            if use_intersection:
                if len(matched_filters) == len(filters):
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched ALL exclude filters (intersection mode)", verbose_only=True, verbose=verbose)
            else:
                if matched_filters:
                    filtered_assets.add(asset_id)
                    log(f"Asset {asset_id} matched at least one exclude filter (union mode)", verbose_only=True, verbose=verbose)
    for desc, count in filter_counts.items():
        log(f"Filter '{desc}' ({'include' if is_include else 'exclude'}, {'intersection' if use_intersection else 'union'} mode) matched {count} assets", verbose_only=False, verbose=verbose)
    return filtered_assets

def parse_filters(filter_inputs, verbose=False):
    filters = []
    for inp in filter_inputs or []:
        data = None
        if os.path.exists(inp):
            data = load_json_file(inp, verbose)
            if data and isinstance(data, list):
                filters.extend(data)
                log(f"Loaded {len(data)} filters from file {inp}", verbose_only=True, verbose=verbose)
            elif data:
                log(f"Filter file {inp} must contain a JSON array", fg="red", verbose_only=False, verbose=verbose)
        else:
            try:
                data = json.loads(inp)
                if isinstance(data, list):
                    filters.extend(data)
                    log(f"Loaded {len(data)} filters from raw JSON value", verbose_only=True, verbose=verbose)
                else:
                    log(f"Raw JSON input must be a JSON array, got {type(data).__name__}", fg="red", verbose_only=False, verbose=verbose)
            except Exception as e:
                parts = inp.split(':', 1)
                if len(parts) == 2:
                    filters.append({"path": parts[0], "regex": parts[1]})
                    log(f"Added filter from command line: {inp}", verbose_only=True, verbose=verbose)
                else:
                    log(f"Error parsing filter input {inp}: {e}", fg="red", verbose_only=False, verbose=verbose)
    return filters

def add_assets_to_album(server_url, api_key, album_id, asset_ids, chunk_size=500, verbose=False):
    url = f"{server_url}/api/albums/{album_id}/assets"
    headers = {"x-api-key": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    total_added = 0
    asset_ids_list = list(asset_ids)
    for i in range(0, len(asset_ids_list), chunk_size):
        chunk = asset_ids_list[i:i+chunk_size]
        payload = {"ids": chunk}
        log(f"Adding chunk of {len(chunk)} assets to album {album_id} ({i+1}-{i+len(chunk)} of {len(asset_ids_list)})", verbose_only=False, verbose=verbose)
        result = api_request('put', url, headers, json_data=payload, verbose=verbose)
        if result is not None:
            total_added += len(chunk)
            for aid in chunk:
                log(f"{server_url}/photos/{aid}", verbose_only=False, verbose=verbose)
    log(f"Added {total_added} of {len(asset_ids_list)} assets to album", 
        fg="green" if total_added == len(asset_ids_list) else "yellow", 
        verbose_only=False, verbose=verbose)
    return total_added

#################################
# BUILDING QUERY NODES (DEFERRED MERGING)
#################################
def build_query_node(query_files, search_type, merge_mode, server, api_key, verbose, all_search_assets):
    """
    For each query file in query_files, execute the search and create a leaf node.
    Then, if more than one node exists, wrap them in a parent node with the specified merge_mode.
    Also, append each search’s assets to all_search_assets (a mutable list).
    """
    nodes = []
    for idx, qf in enumerate(query_files or []):
        query = load_json_file(qf, verbose)
        if not query:
            log(f"Failed to load query from {qf}", fg="red", verbose_only=False, verbose=verbose)
            continue
        assets = execute_search(server, api_key, query, search_type, verbose)
        # Collect assets for later use (e.g. local filtering fallback)
        all_search_assets.extend(assets)
        result_set = {asset["id"] for asset in assets} if assets else set()
        node = {
            "mode": "union",  # Leaf node mode (only one result set)
            "results": {qf: result_set}
        }
        nodes.append(node)
    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    return {"mode": merge_mode, "children": nodes}

#################################
# MAIN FUNCTION
#################################
def main():
    # Check for duplicate arguments.
    seen = {}
    for i, arg in enumerate(sys.argv):
        if arg.startswith('--'):
            if arg in seen:
                log(f"Error: Argument '{arg}' appears multiple times (lines {seen[arg]} and {i})", fg="red", verbose_only=False, verbose=True)
                return 1
            seen[arg] = i

    parser = argparse.ArgumentParser(
        description="Search Immich for photos using metadata and smart search APIs, apply JSONPath and regex filters, and optionally add to an album."
    )
    parser.add_argument("--key", help="Your Immich API Key (env: IMMICH_API_KEY)", default=None)
    parser.add_argument("--server", help="Your Immich server URL (env: IMMICH_SERVER_URL)", default=None)
    parser.add_argument("--album", help="ID of the album to add matching assets to (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging")
    parser.add_argument("--max-assets", type=int, help="Maximum number of assets to process", default=None)

    # Define flags in dictionaries for easier looping.
    smart_include = {"union": "--include-smart-union", "intersection": "--include-smart-intersection"}
    smart_exclude = {"union": "--exclude-smart-union", "intersection": "--exclude-smart-intersection"}
    meta_include  = {"union": "--include-metadata-union", "intersection": "--include-metadata-intersection"}
    meta_exclude  = {"union": "--exclude-metadata-union", "intersection": "--exclude-metadata-intersection"}
    local_include = {"union": "--include-local-filter-union", "intersection": "--include-local-filter-intersection"}
    local_exclude = {"union": "--exclude-local-filter-union", "intersection": "--exclude-local-filter-intersection"}

    for group in [smart_include, smart_exclude, meta_include, meta_exclude, local_include, local_exclude]:
        for mode, flag in group.items():
            parser.add_argument(flag, nargs="+", type=str, help=f"Path to JSON files for {flag} (mode: {mode})")

    args = parser.parse_args()
    if not args.key:
        args.key = os.environ.get("IMMICH_API_KEY")
    if not args.server:
        args.server = os.environ.get("IMMICH_SERVER_URL")
    if not args.key:
        log("Error: API key is required. Set IMMICH_API_KEY environment variable or use --key parameter.", fg="red", verbose_only=False, verbose=args.verbose)
        return 1
    if not args.server:
        log("Error: Server URL is required. Set IMMICH_SERVER_URL environment variable or use --server parameter.", fg="red", verbose_only=False, verbose=args.verbose)
        return 1

    args.server = args.server.rstrip('/')

    # Global list to collect all assets from query searches.
    all_search_assets = []

    #################################
    # Phase 1: Build Nodes for Include & Exclude Searches
    #################################
    include_nodes = []
    # Process both metadata and smart include queries.
    for stype, group in [("metadata", meta_include), ("smart", smart_include)]:
        for m_mode, flag in group.items():
            query_files = getattr(args, flag.lstrip('--').replace('-', '_'))
            node = build_query_node(query_files, stype, m_mode, args.server, args.key, args.verbose, all_search_assets)
            if node is not None:
                include_nodes.append(node)
    # Phase 1 fallback: if no include queries were provided, we'll later fallback to all unique assets.

    exclude_nodes = []
    # Process both metadata and smart exclude queries.
    for stype, group in [("metadata", meta_exclude), ("smart", smart_exclude)]:
        for m_mode, flag in group.items():
            query_files = getattr(args, flag.lstrip('--').replace('-', '_'))
            node = build_query_node(query_files, stype, m_mode, args.server, args.key, args.verbose, all_search_assets)
            if node is not None:
                exclude_nodes.append(node)

    #################################
    # Phase 2: Unique Assets Collection (from all queries)
    #################################
    unique_assets_from_all = {}
    for asset in all_search_assets:
        unique_assets_from_all[asset["id"]] = asset
    log(f"Collected {len(unique_assets_from_all)} unique assets from all search queries", verbose_only=True, verbose=args.verbose)

    #################################
    # Phase 3: Process Local Filters
    #################################
    asset_list = list(unique_assets_from_all.values())
    local_filters = {
        "include": {
            "union": parse_filters(getattr(args, local_include["union"].lstrip('--').replace('-', '_')), args.verbose),
            "intersection": parse_filters(getattr(args, local_include["intersection"].lstrip('--').replace('-', '_')), args.verbose)
        },
        "exclude": {
            "union": parse_filters(getattr(args, local_exclude["union"].lstrip('--').replace('-', '_')), args.verbose),
            "intersection": parse_filters(getattr(args, local_exclude["intersection"].lstrip('--').replace('-', '_')), args.verbose)
        }
    }
    local_include_filters_provided = bool(local_filters["include"]["union"] or local_filters["include"]["intersection"])
    local_include_union = apply_filters(asset_list, local_filters["include"]["union"], is_include=True, use_intersection=False, verbose=args.verbose) if local_filters["include"]["union"] else set()
    local_include_intersection = apply_filters(asset_list, local_filters["include"]["intersection"], is_include=True, use_intersection=True, verbose=args.verbose) if local_filters["include"]["intersection"] else set()
    if local_include_union and local_include_intersection:
        local_include_result = local_include_union.intersection(local_include_intersection)
        log(f"Local include filter result (union ∩ intersection): {len(local_include_result)} assets", verbose_only=False, verbose=args.verbose)
    elif local_include_union:
        local_include_result = local_include_union
        log(f"Local include filter union result: {len(local_include_result)} assets", verbose_only=False, verbose=args.verbose)
    elif local_include_intersection:
        local_include_result = local_include_intersection
        log(f"Local include filter intersection result: {len(local_include_result)} assets", verbose_only=False, verbose=args.verbose)
    else:
        local_include_result = set()

    local_exclude_union = apply_filters(asset_list, local_filters["exclude"]["union"], is_include=False, use_intersection=False, verbose=args.verbose) if local_filters["exclude"]["union"] else set()
    local_exclude_intersection = apply_filters(asset_list, local_filters["exclude"]["intersection"], is_include=False, use_intersection=True, verbose=args.verbose) if local_filters["exclude"]["intersection"] else set()
    local_exclude_result = local_exclude_union.union(local_exclude_intersection)
    if local_exclude_result:
        log(f"Local exclude filter result: {len(local_exclude_result)} assets", verbose_only=False, verbose=args.verbose)

    #################################
    # Phase 4: Build Final Merging Structure
    #################################
    # For the include branch, if no include query nodes were provided, fallback to all unique assets.
    if not include_nodes:
        include_nodes.append({"mode": "intersection", "results": {"all": set(unique_assets_from_all.keys())}})
    # Also add local include filter node if available.
    if local_include_filters_provided:
        include_nodes.append({"mode": "intersection", "results": {"local": local_include_result}})
    include_branch = {"mode": "intersection", "children": include_nodes}

    # For the exclude branch, combine any exclude query nodes and add local exclude node.
    if not exclude_nodes:
        exclude_nodes.append({"mode": "union", "results": {"none": set()}})
    if local_exclude_result:
        exclude_nodes.append({"mode": "union", "results": {"local_exclude": local_exclude_result}})
    exclude_branch = {"mode": "union", "children": exclude_nodes}

    # Final structure subtracts exclude branch from include branch.
    final_structure = {"mode": "minus", "children": [include_branch, exclude_branch]}
    final_asset_ids = compute_merged(final_structure)
    log(f"Final merged asset IDs after applying all criteria: {len(final_asset_ids)} assets", verbose_only=False, verbose=args.verbose)

    #################################
    # Phase 5: Apply Limit and Finalize Output
    #################################
    if final_asset_ids and args.max_assets and len(final_asset_ids) > args.max_assets:
        log(f"Limiting to {args.max_assets} assets (from {len(final_asset_ids)})", verbose_only=False, verbose=args.verbose)
        final_asset_ids = set(list(final_asset_ids)[:args.max_assets])

    if final_asset_ids:
        log(f"\nFinal assets selected: {len(final_asset_ids)}", verbose_only=False, verbose=args.verbose)
        if not args.album:
            for aid in final_asset_ids:
                log(f"{args.server}/photos/{aid}", verbose_only=False, verbose=args.verbose)
        else:
            add_assets_to_album(args.server, args.key, args.album, final_asset_ids, verbose=args.verbose)
    else:
        log("No assets matched all criteria.", fg="yellow", verbose_only=False, verbose=args.verbose)

    return 0

if __name__ == "__main__":
    sys.exit(main())
