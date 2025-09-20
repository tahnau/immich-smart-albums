
import requests
import json
import re
from .logger import log
from tabulate import tabulate

class ImmichAPI:
    def __init__(self, server_url, api_key, verbose=False):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.verbose = verbose
        log(f"Immich Server URL: {self.server_url}", verbose_only=True, verbose=self.verbose)
        log(f"Immich API Key (first 5 chars): {self.api_key[:5]}...", verbose_only=True, verbose=self.verbose)
        self.headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.albums = None

    def _request(self, method, url, params=None, json_data=None):
        log(f"API {method} request to {url}", verbose_only=True, verbose=self.verbose)
        if params:
            log(f"Params: {params}", verbose_only=True, verbose=self.verbose)
        if json_data:
            log(f"Payload: {json_data}", verbose_only=True, verbose=self.verbose)
        try:
            if method.lower() == 'get':
                response = requests.get(url, headers=self.headers, params=params)
            elif method.lower() == 'post':
                response = requests.post(url, headers=self.headers, json=json_data)
            elif method.lower() == 'put':
                response = requests.put(url, headers=self.headers, json=json_data)
            else:
                log(f"Unsupported method: {method}", fg="red", verbose_only=False, verbose=self.verbose)
                return None
            
            log(f"Response status: {response.status_code}", verbose_only=True, verbose=self.verbose)
            text = response.text if len(response.text) <= 4500 else response.text[:4500] + "..."
            log(f"Response: {text}", verbose_only=True, verbose=self.verbose)

            if not response.ok:
                log(f"API request failed: {response.status_code} - {response.text}", fg="red", verbose_only=False, verbose=self.verbose)
                return None
            return response.json() if response.text else None
        except requests.exceptions.RequestException as e:
            log(f"API request error: {str(e)}", fg="red", verbose_only=False, verbose=self.verbose)
            return None

    def get_user_info(self):
        url = f"{self.server_url}/api/users/me"
        log("Fetching current user information...", verbose_only=False, verbose=self.verbose)
        result = self._request('get', url)
        if result:
            log("User information retrieved successfully:", fg="green", verbose_only=False, verbose=self.verbose)
            print(json.dumps({k: result[k] for k in ('id', 'name', 'email', 'isAdmin', 'updatedAt') if k in result}, indent=2))
            return result
        else:
            log("Failed to retrieve user information", fg="red", verbose_only=False, verbose=self.verbose)
            return None

    def _get_albums_data(self):
        if self.albums is not None:
            return self.albums

        log("Fetching all albums...", verbose_only=False, verbose=self.verbose)
        
        # Fetch shared albums
        url_shared = f"{self.server_url}/api/albums?shared=true"
        shared_albums = self._request('get', url_shared)
        if shared_albums is None:
            shared_albums = []

        # Fetch non-shared albums
        url_not_shared = f"{self.server_url}/api/albums?shared=false"
        not_shared_albums = self._request('get', url_not_shared)
        if not_shared_albums is None:
            not_shared_albums = []

        self.albums = shared_albums + not_shared_albums
        return self.albums

    def get_albums(self):
        result = self._get_albums_data()
        if result is not None:
            headers = ["albums-id", "updatedAt", "albumName", "owner-name", "shared", "assetCount"]
            table = []
            for album in result:
                owner_name = album.get('owner', {}).get('name', 'N/A')
                table.append([album.get('id'), album.get('updatedAt'), album.get('albumName'), owner_name, album.get('shared'), album.get('assetCount')])
            print(tabulate(table, headers=headers, tablefmt="simple"))
            print() # Add a newline
            return result
        else:
            log("Failed to retrieve albums", fg="red", verbose_only=False, verbose=self.verbose)
            return None

    def get_album_id_from_name(self, album_name):
        albums = self._get_albums_data()
        if not albums:
            return None

        matching_albums = [a for a in albums if a['albumName'] == album_name]

        if not matching_albums:
            log(f"No album found with name '{album_name}'", fg="red", verbose_only=False, verbose=self.verbose)
            return None
        
        if len(matching_albums) > 1:
            log(f"Multiple albums found with name '{album_name}'. Using the first one.", fg="yellow", verbose_only=False, verbose=self.verbose)

        return matching_albums[0]['id']

    def get_all_users(self):
        url = f"{self.server_url}/api/users"
        log("Fetching all users...", verbose_only=False, verbose=self.verbose)
        result = self._request('get', url)
        if result is not None:
            log("All users retrieved successfully:", fg="green", verbose_only=False, verbose=self.verbose)
            headers = ["users-id", "name"]
            table = []
            for user in result:
                table.append([user.get('id'), user.get('name')])
            print(tabulate(table, headers=headers, tablefmt="simple"))
            print() # Add a newline
            return result
        else:
            log("Failed to retrieve all users. This may require admin privileges.", fg="red", verbose_only=False, verbose=self.verbose)
            return None

    def _fetch_all_people(self):
        url = f"{self.server_url}/api/people"
        all_people = []
        page = 1
        while True:
            params = {'page': page, 'withHidden': 'true'}
            response_data = self._request('get', url, params=params)
            if response_data is None or not response_data.get('people'):
                break
            all_people.extend(response_data['people'])
            page += 1
        return all_people

    def get_people(self):
        log("Fetching all named people...", verbose_only=False, verbose=self.verbose)
        all_people = self._fetch_all_people()
        if all_people:
            log("Named people retrieved successfully:", fg="green", verbose_only=False, verbose=self.verbose)
            headers = ["people-id", "name"]
            table = []
            found_named = False
            for person in all_people:
                if person.get('name'):
                    found_named = True
                    table.append([person.get('id'), person.get('name')])
            if not found_named:
                log("No people with names found.", fg="yellow", verbose_only=False, verbose=self.verbose)
            else:
                print(tabulate(table, headers=headers, tablefmt="simple"))
            print() # Add a newline
            return all_people
        else:
            log("Failed to retrieve any people.", fg="red", verbose_only=False, verbose=self.verbose)
            return None

    def get_person_ids_from_names(self, identifiers, all_people):
        person_map = {}
        for person in all_people:
            if 'name' in person and person['name']:
                if person['name'] not in person_map:
                    person_map[person['name']] = []
                person_map[person['name']].append(person['id'])

        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        resolved_ids = []
        for identifier in identifiers:
            if uuid_regex.match(identifier):
                resolved_ids.append(identifier)
                log(f"Identifier '{identifier}' is a UUID, using it directly.", verbose_only=True, verbose=self.verbose)
                continue
            
            if identifier in person_map:
                ids = person_map[identifier]
                if len(ids) > 1:
                    log(f"Warning: Found multiple people named '{identifier}'. Resolving to all of them: {ids}", fg="yellow", verbose_only=False, verbose=self.verbose)
                resolved_ids.extend(ids)
                for person_id in ids:
                    log(f"Resolved person name '{identifier}' to ID '{person_id}'.", verbose_only=True, verbose=self.verbose)
            else:
                log(f"Could not find a person with name or UUID '{identifier}'.", fg="yellow", verbose_only=False, verbose=self.verbose)
        return resolved_ids

    def execute_search(self, query, search_type):
        url = f"{self.server_url}/api/search/{search_type}"
        result_limit = query.get("resultLimit") if query and "resultLimit" in query else None
        if result_limit:
            log(f"Using result limit: {result_limit} for {search_type} search", verbose_only=True, verbose=self.verbose)
        
        all_assets = []
        page = 1
        size = 100
        while True:
            payload = query.copy() if query else {}
            payload["page"] = page
            payload["withExif"] = True
            payload["size"] = size
            
            log(f"Executing {search_type} search (page {page})", verbose_only=True, verbose=self.verbose)
            result = self._request('post', url, json_data=payload)
            
            if not result or "assets" not in result:
                log(f"Search returned no valid results on page {page}", fg="yellow", verbose_only=True, verbose=self.verbose)
                break

            assets = result.get("assets", {}).get("items", [])
            all_assets.extend(assets)

            if result_limit and len(all_assets) >= result_limit:
                log(f"Reached result limit ({result_limit}), stopping search", verbose_only=True, verbose=self.verbose)
                all_assets = all_assets[:result_limit]
                break

            if result.get("assets", {}).get("nextPage") is None:
                log(f"Reached last page ({page}), total assets: {len(all_assets)}", verbose_only=True, verbose=self.verbose)
                break
                
            log(f"Retrieved {len(assets)} assets from page {page}", verbose_only=True, verbose=self.verbose)
            page += 1
            
        return all_assets

    def add_assets_to_album(self, album_id, asset_ids, chunk_size=500):
        url = f"{self.server_url}/api/albums/{album_id}/assets"
        total_added = 0
        asset_ids_list = list(asset_ids)
        for i in range(0, len(asset_ids_list), chunk_size):
            chunk = asset_ids_list[i:i+chunk_size]
            payload = {"ids": chunk}
            log(f"Adding chunk of {len(chunk)} assets to album {album_id} ({i+1}-{i+len(chunk)} of {len(asset_ids_list)})", verbose_only=False, verbose=self.verbose)
            result = self._request('put', url, json_data=payload)
            if result is not None:
                total_added += len(chunk)
                for aid in chunk:
                    log(f"{self.server_url}/photos/{aid}", verbose_only=False, verbose=self.verbose)
        
        log(f"Added {total_added} of {len(asset_ids_list)} assets to album", 
            fg="green" if total_added == len(asset_ids_list) else "yellow", 
            verbose_only=False, verbose=self.verbose)
        return total_added
