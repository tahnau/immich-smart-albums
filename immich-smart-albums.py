#!/usr/bin/env python3
import sys
import re
from functools import reduce

from lib.logger import log
from lib.api import ImmichAPI
from lib.config import get_config, has_search_actions
from lib.filter import Filter, normalize_query, load_json_file, normalize_json_query


def get_asset_set(assets):
    return {asset['id'] for asset in assets}


def _process_filters(
    immich_api,
    all_search_assets,
    union_rules,
    intersection_rules,
    search_type='metadata',
    default_smart_result_limit=200
):
    union_assets = set()
    if union_rules:
        for rule in union_rules:
            if search_type == 'smart':
                query = normalize_query(rule, default_smart_result_limit, immich_api.verbose)
            else:
                query = normalize_json_query(rule, immich_api.verbose)

            if query:
                assets = immich_api.execute_search(query, search_type)
                all_search_assets.extend(assets)
                union_assets.update(get_asset_set(assets))

    intersection_assets = set()
    if intersection_rules:
        all_intersection_sets = []
        for rule in intersection_rules:
            if search_type == 'smart':
                query = normalize_query(rule, default_smart_result_limit, immich_api.verbose)
            else:
                query = normalize_json_query(rule, immich_api.verbose)

            if query:
                assets = immich_api.execute_search(query, search_type)
                all_search_assets.extend(assets)
                all_intersection_sets.append(get_asset_set(assets))

        if all_intersection_sets:
            intersection_assets = set.intersection(*all_intersection_sets)

    if union_rules and intersection_rules:
        return union_assets.intersection(intersection_assets)
    elif union_rules:
        return union_assets
    elif intersection_rules:
        return intersection_assets
    else:
        return None


def process_query_filters(filter_type, args, immich_api, all_search_assets):
    """Processes query-based filters (metadata, smart) for include and exclude."""

    include_union_files = getattr(args, f"include_{filter_type}_union", None)
    include_intersection_files = getattr(
        args, f"include_{filter_type}_intersection", None)

    include_assets = _process_filters(
        immich_api,
        all_search_assets,
        include_union_files,
        include_intersection_files,
        search_type=filter_type,
        default_smart_result_limit=args.default_smart_result_limit
    )

    exclude_union_files = getattr(args, f"exclude_{filter_type}_union", None)
    exclude_intersection_files = getattr(
        args, f"exclude_{filter_type}_intersection", None)

    exclude_assets = _process_filters(
        immich_api,
        all_search_assets,
        exclude_union_files,
        exclude_intersection_files,
        search_type=filter_type,
        default_smart_result_limit=args.default_smart_result_limit
    )

    return include_assets, exclude_assets or set()


def process_person_filters(args, immich_api, all_search_assets):
    """Processes person name filters for include and exclude."""

    # Includes
    person_includes = None
    include_union_assets = set()
    if args.include_person_ids_union:
        for person_id in args.include_person_ids_union:
            assets = immich_api.execute_search({"personIds": [person_id]}, "metadata")
            all_search_assets.extend(assets)
            include_union_assets.update(get_asset_set(assets))

    include_intersection_assets = set()
    if args.include_person_ids_intersection:
        intersection_sets = []
        for person_id in args.include_person_ids_intersection:
            assets = immich_api.execute_search({"personIds": [person_id]}, "metadata")
            all_search_assets.extend(assets)
            intersection_sets.append(get_asset_set(assets))
        if intersection_sets:
            include_intersection_assets = set.intersection(*intersection_sets)

    if args.include_person_ids_union and args.include_person_ids_intersection:
        person_includes = include_union_assets.intersection(include_intersection_assets)
    elif args.include_person_ids_union:
        person_includes = include_union_assets
    elif args.include_person_ids_intersection:
        person_includes = include_intersection_assets

    # Excludes
    person_excludes = set()
    if args.exclude_person_ids_union:
        for person_id in args.exclude_person_ids_union:
            assets = immich_api.execute_search({"personIds": [person_id]}, "metadata")
            all_search_assets.extend(assets)
            person_excludes.update(get_asset_set(assets))

    if args.exclude_person_ids_intersection:
        intersection_sets = []
        for person_id in args.exclude_person_ids_intersection:
            assets = immich_api.execute_search({"personIds": [person_id]}, "metadata")
            all_search_assets.extend(assets)
            intersection_sets.append(get_asset_set(assets))
        if intersection_sets:
            person_excludes.update(set.intersection(*intersection_sets))

    return person_includes, person_excludes

def process_local_filters(args, asset_list_for_local_filtering):
    """Processes local filters for include and exclude."""

    local_filter = Filter(args.verbose)
    local_include_union_filters = local_filter.parse_filters(
        args.include_local_filter_union)
    local_include_intersection_filters = local_filter.parse_filters(
        args.include_local_filter_intersection)
    local_exclude_union_filters = local_filter.parse_filters(
        args.exclude_local_filter_union)
    local_exclude_intersection_filters = local_filter.parse_filters(
        args.exclude_local_filter_intersection)

    local_include_assets = None
    if local_include_union_filters or local_include_intersection_filters:
        local_includes_union = local_filter.apply_local_filters(
            asset_list_for_local_filtering, local_include_union_filters, is_include=True, use_intersection=False)
        local_includes_intersection = local_filter.apply_local_filters(
            asset_list_for_local_filtering, local_include_intersection_filters, is_include=True, use_intersection=True)

        if local_include_union_filters and local_include_intersection_filters:
            local_include_assets = local_includes_union.intersection(
                local_includes_intersection)
        elif local_include_union_filters:
            local_include_assets = local_includes_union
        else:
            local_include_assets = local_includes_intersection

    local_excludes_union = local_filter.apply_local_filters(
        asset_list_for_local_filtering, local_exclude_union_filters, is_include=False, use_intersection=False)
    local_excludes_intersection = local_filter.apply_local_filters(
        asset_list_for_local_filtering, local_exclude_intersection_filters, is_include=False, use_intersection=True)
    local_exclude_assets = local_excludes_union.union(
        local_excludes_intersection)

    return local_include_assets, local_exclude_assets

def get_final_asset_ids(args, immich_api, all_search_assets, metadata_includes, smart_includes, person_includes, metadata_excludes, smart_excludes, person_excludes):
    # Combine all includes
    include_sets = [s for s in [
        metadata_includes, smart_includes, person_includes] if s is not None]
    if not include_sets:
        # If no include filters are specified, start with all assets from exclude queries
        # This is because local filters need a base set of assets to work with.
        unique_assets_from_all = {
            asset["id"]: asset for asset in all_search_assets}
        final_included_assets = set(unique_assets_from_all.keys())
    else:
        final_included_assets = set.intersection(*include_sets)

    # Process Local Filters
    unique_assets_from_all = {
        asset["id"]: asset for asset in all_search_assets}
    asset_list_for_local_filtering = [unique_assets_from_all[asset_id]
                                      for asset_id in final_included_assets if asset_id in unique_assets_from_all]

    local_include_assets, local_exclude_assets = process_local_filters(
        args, asset_list_for_local_filtering)

    if local_include_assets is not None:
        final_included_assets = final_included_assets.intersection(
            local_include_assets)

    # Combine all excludes
    final_excluded_assets = metadata_excludes.union(
        smart_excludes, person_excludes, local_exclude_assets)

    # Final Calculation
    final_asset_ids = final_included_assets - final_excluded_assets

    return final_asset_ids

def resolve_and_validate_names(args, immich_api):
    """Fetch all people and albums to validate names early."""
    all_people_data = None
    if args.include_person_names_union or args.include_person_names_intersection or \
       args.exclude_person_names_union or args.exclude_person_names_intersection:
        all_people_data = immich_api._fetch_all_people()
        if not all_people_data:
            log("Could not fetch people data from Immich.", fg="red")
            sys.exit(1)

    if args.album:
        album_id = args.album
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        if not uuid_regex.match(album_id):
            log(f"Album '{album_id}' is not a UUID, resolving to ID...", verbose_only=False, verbose=args.verbose)
            resolved_album_id = immich_api.get_album_id_from_name(album_id)
            if not resolved_album_id:
                log(f"Album '{album_id}' not found.", fg="red")
                sys.exit(1)
            args.album = resolved_album_id

    person_name_args = {
        'include_person_names_union': 'include_person_ids_union',
        'include_person_names_intersection': 'include_person_ids_intersection',
        'exclude_person_names_union': 'exclude_person_ids_union',
        'exclude_person_names_intersection': 'exclude_person_ids_intersection'
    }
    for name_arg, id_arg in person_name_args.items():
        person_names = getattr(args, name_arg)
        if person_names:
            resolved_ids = []
            unresolved_names = []
            for name in set(person_names):
                ids = immich_api.get_person_ids_from_names([name], all_people_data)
                if ids:
                    resolved_ids.extend(ids)
                else:
                    unresolved_names.append(name)
            
            if unresolved_names:
                log(f"Could not resolve the following person names: {', '.join(unresolved_names)}. Exiting.", fg="red")
                sys.exit(1)

            setattr(args, id_arg, resolved_ids)

def main():
    args = get_config()

    if not args.key or not args.server:
        log("API key and server URL are required.", fg="red")
        return 1

    immich_api = ImmichAPI(args.server, args.key, args.verbose)

    resolve_and_validate_names(args, immich_api)

    if not has_search_actions(args):
        log("No search actions specified. Displaying info.",
            verbose_only=False, verbose=args.verbose)
        immich_api.get_user_info()
        immich_api.get_albums()
        immich_api.get_all_users()
        immich_api.get_people()
        return 0

    all_search_assets = []

    # Process Metadata and Smart filters
    metadata_includes, metadata_excludes = process_query_filters(
        "metadata", args, immich_api, all_search_assets)
    smart_includes, smart_excludes = process_query_filters(
        "smart", args, immich_api, all_search_assets)

    # Process Person name filters
    person_includes, person_excludes = process_person_filters(
        args, immich_api, all_search_assets)

    final_asset_ids = get_final_asset_ids(args, immich_api, all_search_assets, metadata_includes, smart_includes, person_includes, metadata_excludes, smart_excludes, person_excludes)

    log(f"Final merged asset IDs after applying all criteria: {len(final_asset_ids)} assets",
        verbose_only=False, verbose=args.verbose)

    if final_asset_ids and args.max_assets and len(final_asset_ids) > args.max_assets:
        log(f"Limiting to {args.max_assets} assets (from {len(final_asset_ids)})",
            verbose_only=False, verbose=args.verbose)
        final_asset_ids = set(list(final_asset_ids)[:args.max_assets])

    if final_asset_ids:
        log(f"\nFinal assets selected: {len(final_asset_ids)}",
            verbose_only=False, verbose=args.verbose)
        if not args.album:
            for aid in sorted(list(final_asset_ids)):
                log(f"{immich_api.server_url}/photos/{aid}",
                    verbose_only=False, verbose=args.verbose)
        else:
            album_id = args.album
            if album_id:
                immich_api.add_assets_to_album(album_id, final_asset_ids)
    else:
        log("No assets matched all criteria.", fg="yellow",
            verbose_only=False, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
