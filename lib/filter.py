import json
import os
import re
from jsonpath_ng import parse
from .logger import log

def normalize_json_query(query_input, verbose=False):
    """Parses a query input, which can be a file path or a JSON string."""
    # Try parsing as JSON string first
    try:
        data = json.loads(query_input)
        if isinstance(data, dict):
            log(f"Parsed as JSON string: {data}", verbose_only=True, verbose=verbose)
            return data
    except json.JSONDecodeError:
        pass  # Not a valid JSON string, proceed to file check

    # Check if it's a file path
    if os.path.exists(str(query_input)) and str(query_input).endswith('.json'):
        return load_json_file(query_input, verbose)

    return None


def normalize_query(query_input, default_result_limit, verbose=False):
    """Parses a query input, which can be a file path, a JSON string, a plain query, or a query with a result limit.
    Ensures the output is a dictionary with 'query' and 'resultLimit'."""
    
    # Try to parse as JSON file or string
    json_data = normalize_json_query(query_input, verbose)
    if json_data:
        if 'resultLimit' not in json_data:
            json_data['resultLimit'] = default_result_limit
        return json_data

    # Handle 'query @limit' shorthand and plain query for smart searches
    match = re.match(r'^(.*)\s*@\s*(\d+)$', query_input)
    if match:
        query = match.group(1).strip()
        limit = int(match.group(2))
        log(f"Parsed as query with limit: '{query}' @ {limit}", verbose_only=True, verbose=verbose)
        return {"query": query, "resultLimit": limit}
    
    # Treat as a plain query string
    log(f"Parsed as plain query: '{query_input}'", verbose_only=True, verbose=verbose)
    return {"query": query_input, "resultLimit": default_result_limit}


def load_json_file(file_path, verbose=False):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        log(f"Successfully loaded JSON from {file_path}", verbose_only=True, verbose=verbose)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log(f"Error loading JSON file {file_path}: {str(e)}", fg="red", verbose_only=False, verbose=verbose)
        return None

class Filter:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def parse_filters(self, filter_inputs):
        filters = []
        for inp in filter_inputs or []:
            data = None
            if os.path.exists(inp):
                data = load_json_file(inp, self.verbose)
                if data and isinstance(data, list):
                    filters.extend(data)
                    log(f"Loaded {len(data)} filters from file {inp}", verbose_only=True, verbose=self.verbose)
                elif data:
                    log(f"Filter file {inp} must contain a JSON array", fg="red", verbose_only=False, verbose=self.verbose)
            else:
                try:
                    data = json.loads(inp)
                    if isinstance(data, list):
                        filters.extend(data)
                        log(f"Loaded {len(data)} filters from raw JSON value", verbose_only=True, verbose=self.verbose)
                    else:
                        log(f"Raw JSON input must be a JSON array, got {type(data).__name__}", fg="red", verbose_only=False, verbose=self.verbose)
                except Exception as e:
                    parts = inp.split(':', 1)
                    if len(parts) == 2:
                        filters.append({"path": parts[0], "regex": parts[1]})
                        log(f"Added filter from command line: {inp}", verbose_only=True, verbose=self.verbose)
                    else:
                        log(f"Error parsing filter input {inp}: {e}", fg="red", verbose_only=False, verbose=self.verbose)
        return filters

    def apply_local_filters(self, assets, filters, is_include=True, use_intersection=True):
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
                                log(f"Asset {asset_id} matched filter: {description}", verbose_only=True, verbose=self.verbose)
                        else:
                            matched_filters.add(description)
                            asset_matches[asset_id].add(description)
                            filter_counts[description] += 1
                            log(f"Asset {asset_id} matched path: {path}", verbose_only=True, verbose=self.verbose)
                except Exception as e:
                    log(f"JSONPath error for asset {asset_id} with expression '{path}': {str(e)}", fg="red", verbose_only=True, verbose=self.verbose)

            if is_include:
                if use_intersection:
                    if len(matched_filters) == len(filters):
                        filtered_assets.add(asset_id)
                        log(f"Asset {asset_id} matched ALL include filters (intersection mode)", verbose_only=True, verbose=self.verbose)
                else:
                    if matched_filters:
                        filtered_assets.add(asset_id)
                        log(f"Asset {asset_id} matched at least one include filter (union mode)", verbose_only=True, verbose=self.verbose)
            else: # is_exclude
                if use_intersection:
                    if len(matched_filters) == len(filters):
                        filtered_assets.add(asset_id)
                        log(f"Asset {asset_id} matched ALL exclude filters (intersection mode)", verbose_only=True, verbose=self.verbose)
                else:
                    if matched_filters:
                        filtered_assets.add(asset_id)
                        log(f"Asset {asset_id} matched at least one exclude filter (union mode)", verbose_only=True, verbose=self.verbose)

        for desc, count in filter_counts.items():
            log(f"Filter '{desc}' ({'include' if is_include else 'exclude'}, {'intersection' if use_intersection else 'union'} mode) matched {count} assets", verbose_only=False, verbose=self.verbose)
        
        return filtered_assets