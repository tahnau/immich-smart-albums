#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || { echo "Failed to change directory"; exit 1; }

# Create JSON config files inline
echo '{"personIds":["8fbe472e-7463-4d97-ae2d-3efb3270e153"],"takenAfter":"2015-04-11T00:00:00.000Z"}' > filters/accountPerson1_facePerson1.json
echo '{"personIds":["1918270a-5c60-4504-ae0b-e1b6382c7cd8"]}' > filters/accountPerson1_facePerson2.json
echo '{"personIds":["60e5f100-ef96-42e9-9cc7-cc865c0639d6"]}' > filters/accountPerson1_facePerson3.json
echo '{"personIds":["a49406a0-fa05-4d15-90c9-20b025c0be81"]}' > filters/accountPerson2_facePerson1.json
echo '{"personIds":["9cd73e18-11d5-4a0b-bbe3-650a961ce690"]}' > filters/accountPerson2_facePerson2.json
echo '{"personIds":["34a5f538-5650-4933-9d2a-832da71766c7"]}' > filters/accountPerson2_facePerson3.json
echo '{"query":"nsfw", "resultLimit":300}' > filters/smart-nsfw-1.json
echo '{"query":"nudity", "resultLimit":300}' > filters/smart-nsfw-2.json
echo '{"query":"porn", "resultLimit":300}' > filters/smart-nsfw-3.json
echo '{"query":"nude", "resultLimit":300}' > filters/smart-nsfw-4.json

echo '{"takenBefore":"2015-04-11T00:00:00.000Z"}' > filters/metadataTakenBefore2015.json
echo '[ { "path": "$.originalPath", "regex": "^/trip/2014-11-18", "description": "Files from trip with path starting with /trip/2014-11-18" } ]' > filters/localfilter-2014-11-18.json


# Define album IDs
FAMILY_ALBUM="0a750717-7bc7-4a73-b4c4-405fb0888ba3"
PUBLIC_ALBUM="bb8ee34a-a22d-4bb9-aa67-d394353a06c0"
export IMMICH_SERVER_URL=http://127.0.0.1:2283

source secrets.sh
# Create a secrets.sh file:
#   export IMMICH_API_KEY_1=aaaaaaaaaaaa
#   export IMMICH_API_KEY_2=bbbbbbbbbbbb

# Person1's account
export IMMICH_API_KEY="$IMMICH_API_KEY_1"
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson1_facePerson1.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson1_facePerson2.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson1_facePerson3.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson1_facePerson3.json --album $PUBLIC_ALBUM --exclude-smart-file filters/smart-nsfw-*.json
#python3 immich-smart-albums.py --include-metadata-file filters/metadataTakenBefore2015.json --include-local-filter-file filters/localfilter-2014-11-18.json

# Person2's account
export IMMICH_API_KEY="$IMMICH_API_KEY_2"
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson2_facePerson1.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson2_facePerson2.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson2_facePerson3.json --album $FAMILY_ALBUM
python3 immich-smart-albums.py --include-metadata-file filters/accountPerson2_facePerson3.json --album $PUBLIC_ALBUM --exclude-smart-file filters/smart-nsfw-*.json
