
import argparse
import os
import sys
from dotenv import load_dotenv

def get_config():
    load_dotenv()



    parser = argparse.ArgumentParser(
        description="Search Immich for photos using metadata and smart search APIs, apply JSONPath and regex filters, and optionally add to an album."
    )
    parser.add_argument("--key", help="Your Immich API Key (env: IMMICH_API_KEY)", default=None)
    parser.add_argument("--server", help="Your Immich server URL (env: IMMICH_SERVER_URL)", default=None)
    parser.add_argument("--album", help="ID of the album to add matching assets to (optional)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging")
    parser.add_argument("--max-assets", type=int, help="Maximum number of assets to process after all filters are applied. This limits both the console output (in preview mode) and the number of assets added to an album. Note: Selection is arbitrary as it operates on an unordered set.", default=None)
    parser.add_argument("--default-smart-result-limit", type=int, help="Default result limit for smart searches. This is a global setting with a default value of 200. It can be adjusted per query using the '@' notation (e.g., 'dog@500').", default=200)

    # Define flags in dictionaries for easier looping.
    smart_include = {"union": "--include-smart-union", "intersection": "--include-smart-intersection"}
    smart_exclude = {"union": "--exclude-smart-union", "intersection": "--exclude-smart-intersection"}
    meta_include  = {"union": "--include-metadata-union", "intersection": "--include-metadata-intersection"}
    meta_exclude  = {"union": "--exclude-metadata-union", "intersection": "--exclude-metadata-intersection"}
    local_include = {"union": "--include-local-filter-union", "intersection": "--include-local-filter-intersection"}
    local_exclude = {"union": "--exclude-local-filter-union", "intersection": "--exclude-local-filter-intersection"}

    # Add arguments for person names with explicit logic
    parser.add_argument("--include-person-names-union", nargs="+", type=str, help="Include assets containing ANY of these person names (union).")
    parser.add_argument("--include-person-names-intersection", nargs="+", type=str, help="Include assets containing ALL of these person names (intersection).")
    parser.add_argument("--exclude-person-names-union", nargs="+", type=str, help="Exclude assets containing ANY of these person names (union).")
    parser.add_argument("--exclude-person-names-intersection", nargs="+", type=str, help="Exclude assets containing ALL of these person names (intersection).")

    parser.add_argument("--include-person-ids-union", nargs="+", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--include-person-ids-intersection", nargs="+", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--exclude-person-ids-union", nargs="+", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--exclude-person-ids-intersection", nargs="+", type=str, help=argparse.SUPPRESS)

    for group in [smart_include, smart_exclude, meta_include, meta_exclude, local_include, local_exclude]:
        for mode, flag in group.items():
            parser.add_argument(flag, nargs="+", type=str, help=f"Path to JSON files for {flag} (mode: {mode})")

    args = parser.parse_args()
    if args.key is None:
        args.key = os.environ.get("IMMICH_API_KEY")
    if args.server is None:
        args.server = os.environ.get("IMMICH_SERVER_URL")

    return args

def has_search_actions(args):
    search_flags = [
        'include_smart_union', 'include_smart_intersection',
        'exclude_smart_union', 'exclude_smart_intersection',
        'include_metadata_union', 'include_metadata_intersection',
        'exclude_metadata_union', 'exclude_metadata_intersection',
        'include_local_filter_union', 'include_local_filter_intersection',
        'exclude_local_filter_union', 'exclude_local_filter_intersection',
        'include_person_names_union', 'include_person_names_intersection',
        'exclude_person_names_union', 'exclude_person_names_intersection',
        'include_person_ids_union', 'include_person_ids_intersection',
        'exclude_person_ids_union', 'exclude_person_ids_intersection'
    ]
    
    for flag in search_flags:
        if hasattr(args, flag) and getattr(args, flag):
            return True
    
    return False
