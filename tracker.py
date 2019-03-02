#!/usr/bin/python3

import argparse
import json
import logging
import time
import urllib.parse
import requests

def search_artist(artist_name):
    """Get a list of candidate artists from MusicBrainz given their name."""
    uri = 'https://musicbrainz.org/ws/2/artist?query={}&fmt=json'
    qstr = urllib.parse.quote_plus(artist_name)
    while True:
        logging.info("Querying MusicBrainz for artist=%s", artist_name)
        page = requests.get(uri.format(qstr))
        if page.status_code == 200:
            break
        logging.warning("MusicBrainz returned status=%d", page.status_code)
        time.sleep(5)
    j = json.loads(page.content.decode('utf-8'))
    matches = []
    for artist in j.get('artists', []):
        if artist['name'] == artist_name or artist['score'] == 100:
            if artist.get('disambiguation'):
                artist['dispname'] = "{} ({})".format(artist['name'], artist['disambiguation'])
            else:
                artist['dispname'] = artist['name']
            matches.append(artist)
    return matches

def get_releases_artist(art_id):
    """Get a given artist's release groups from MusicBrainz."""
    uri = "http://musicbrainz.org/ws/2/artist/{}?inc=release-groups&fmt=json"
    while True:
        logging.info("Querying MusicBrainz for artist_id:%s", art_id)
        page = requests.get(uri.format(art_id))
        if page.status_code == 200:
            break
        logging.warning("MusicBrainz returned status=%d", page.status_code)
        time.sleep(5)
    j = json.loads(page.content.decode('utf-8'))
    releases = j['release-groups']
    del j['release-groups']
    for release in releases:
        release['artist'] = j
    return releases

def get_releases(artist_ids):
    """Given a list of artist IDs, get all of their release groups from MusicBrainz."""
    all_releases = []
    for art_id in artist_ids:
        releases = get_releases_artist(art_id)
        all_releases.extend(releases)
    all_releases = sorted(all_releases,
                          key=lambda r: r['first-release-date'],
                          reverse=True)
    return all_releases

def print_releases(releases):
    """Print all releases to console."""
    for release in releases:
        print("{} {} - {}".format(
            release['first-release-date'].ljust(10),
            release['artist']['name'],
            release['title']))

def lookup(kvs):
    """Given a dictionary of Artist:ID mappings, attempt to resolve any Artist IDs that are missing."""
    changed = False
    failure = False
    for k, v in kvs.items():
        if v:
            continue
        print("Lookup on {}".format(k))
        matches = search_artist(k)
        if len(matches) == 1:
            match = matches[0]
            kvs[k] = match['id']
            changed = True
            print("Found Artist match with high confidence:")
            print("{:s} ({:d}%) {:s}".format(match['dispname'], match['score'], match['id']))
        else:
            failure = True
            print("Found multiple candidates, please select manually:")
            for match in matches:
                print("{:s} ({:d}%) {:s}".format(match['dispname'], match['score'], match['id']))
    return changed, failure

def main():
    """It's main(); you love it, you need it."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', metavar='ids', type=str, nargs='+', help="List of MusicBrainz Artist IDs")
    parser.add_argument('--artists', metavar='artists', type=str, nargs='+', help="List of Artist names")
    parser.add_argument('--json', metavar='json_file', type=str, action='store', help="JSON file to load/store Artists")
    parser.add_argument('-v', dest="verbose", action='store_true', default=False, help="Debug output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    kvs = {}
    rewrite = False
    fail = False

    if args.artists:
        kvs.update({k:None for k in args.artists})

    if args.json:
        try:
            with open(args.json, "r") as f:
                j = json.load(f)
                kvs.update(j)
        except FileNotFoundError:
            pass

    if kvs:
        rewrite, fail = lookup(kvs)

    if kvs and rewrite and args.json:
        with open(args.json, "w") as f:
            json.dump(kvs, f, indent=4)

    if fail:
        print("Couldn't look up all artists, exiting.")
        return

    artist_ids = list(kvs.values())
    if args.ids:
        artist_ids.extend(args.artist_ids)

    releases = get_releases(artist_ids)
    print_releases(releases)


if __name__ == '__main__':
    main()
