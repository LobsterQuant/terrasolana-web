#!/usr/bin/env python3
"""
refresh-photos.py — Fetch real Idealista property thumbnails via Apify
and update photo_url fields in listings.json.

Cost: ~$0.03/property on FREE Apify plan (200 free/month).
Run weekly to refresh signed URLs before they expire (~24h).

Usage:
  python3 scripts/refresh-photos.py              # dry run
  python3 scripts/refresh-photos.py --execute    # actually run Apify + update
  python3 scripts/refresh-photos.py --status     # check last run status

Environment:
  APIFY_TOKEN — required
"""

import json, os, sys, time, argparse
from pathlib import Path
import urllib.request as req

BASE_DIR = Path(__file__).parent.parent
LISTINGS_PATH = BASE_DIR / 'data' / 'listings.json'
PHOTO_CACHE_PATH = BASE_DIR / 'data' / 'photo-cache.json'

APIFY_TOKEN = os.environ.get('APIFY_TOKEN', '')
ACTOR_ID = '0qnMmz76dLymEDVGf'  # smart-idealista-scraper

# Search URLs targeting our listing price ranges
SEARCH_URLS = [
    # Almería — cheapest inventory, best yield listings
    'https://www.idealista.com/venta-viviendas/almeria/almeria-capital/?precio-max=300000&ordenado-por=precio-asc',
    'https://www.idealista.com/venta-viviendas/almeria/almeria-capital/?precio-min=300000&ordenado-por=precio-asc',
    # Madrid
    'https://www.idealista.com/venta-viviendas/madrid/madrid-capital/?precio-max=600000&ordenado-por=precio-asc',
    'https://www.idealista.com/venta-viviendas/madrid/madrid-capital/?precio-min=600000&precio-max=2000000&ordenado-por=precio-asc',
    # Valencia
    'https://www.idealista.com/venta-viviendas/valencia/valencia/?precio-max=700000&ordenado-por=precio-asc',
    'https://www.idealista.com/venta-viviendas/valencia/valencia/?precio-min=700000&ordenado-por=precio-asc',
    # Alicante
    'https://www.idealista.com/venta-viviendas/alicante/alicante/?precio-max=1000000&ordenado-por=precio-asc',
    'https://www.idealista.com/venta-viviendas/alicante/alicante/?precio-min=1000000&ordenado-por=precio-asc',
    # Málaga
    'https://www.idealista.com/venta-viviendas/malaga/malaga/?precio-max=1000000&ordenado-por=precio-asc',
    'https://www.idealista.com/venta-viviendas/malaga/malaga/?precio-min=1000000&ordenado-por=precio-asc',
]

def apify_post(path, payload):
    url = f'https://api.apify.com/v2{path}?token={APIFY_TOKEN}'
    data = json.dumps(payload).encode()
    r = req.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with req.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read())

def apify_get(path):
    url = f'https://api.apify.com/v2{path}?token={APIFY_TOKEN}'
    with req.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())

def run_scrape(dry_run=False):
    listings = json.load(open(LISTINGS_PATH))
    our_ids = {str(l['id']) for l in listings if 'MOCK' not in str(l['id'])}
    print(f'Our listings: {len(our_ids)} real IDs')

    if dry_run:
        print('[DRY RUN] Would submit search URLs to Apify:')
        for u in SEARCH_URLS:
            print(f'  {u}')
        est_items = len(SEARCH_URLS) * 40
        est_cost = len(SEARCH_URLS) * 0.005 + min(est_items, 200) * 0 + max(0, est_items - 200) * 0.03
        print(f'Est. items: {est_items} | Est. cost: ${est_cost:.2f}')
        return

    if not APIFY_TOKEN:
        print('ERROR: APIFY_TOKEN not set')
        sys.exit(1)

    print(f'Submitting {len(SEARCH_URLS)} search URLs to Apify...')
    result = apify_post(
        f'/acts/{ACTOR_ID}/runs',
        {'startUrls': [{'url': u} for u in SEARCH_URLS], 'maxItems': 400}
    )
    run_id = result.get('data', {}).get('id')
    dataset_id = result.get('data', {}).get('defaultDatasetId')
    print(f'Run: {run_id} | Dataset: {dataset_id}')

    # Poll for completion
    for i in range(120):
        time.sleep(10)
        status_data = apify_get(f'/actor-runs/{run_id}').get('data', {})
        status = status_data.get('status', '')
        charged = status_data.get('chargedEventCounts', {}).get('PropertyExtracted', 0)
        cost = status_data.get('usageTotalUsd', 0)
        print(f'  {i+1}: {status} | charged: {charged} | cost: ${cost:.3f}')
        if status in ('SUCCEEDED', 'FAILED', 'ABORTED'):
            break

    # Download results
    items_data = apify_get(f'/datasets/{dataset_id}/items?limit=1000')
    print(f'Downloaded {len(items_data)} items')

    # Build photo map
    photo_map = {}
    for item in items_data:
        code = str(item.get('propertyCode', ''))
        thumb = item.get('thumbnail', '')
        if code and thumb:
            photo_map[code] = thumb

    # Match against our listings
    matched = {k: v for k, v in photo_map.items() if k in our_ids}
    print(f'Matched {len(matched)}/{len(our_ids)} listings ({len(matched)/len(our_ids)*100:.1f}%)')

    # Load existing cache
    cache = {}
    if PHOTO_CACHE_PATH.exists():
        cache = json.load(open(PHOTO_CACHE_PATH))

    # Merge: new matches override old ones (fresher signed URLs)
    cache.update(matched)
    json.dump(cache, open(PHOTO_CACHE_PATH, 'w'), indent=2)
    print(f'Cache now has {len(cache)} photos')

    # Update listings.json with proxy URLs for matched listings
    updated = 0
    for listing in listings:
        lid = str(listing['id'])
        if lid in matched:
            # Use proxy URL so signed URL is cached at Vercel edge
            signed_url = matched[lid]
            city = listing.get('city', '')
            listing['photo_url'] = f'/api/img?url={req.quote(signed_url, safe="")}&city={city}'
            updated += 1

    json.dump(listings, open(LISTINGS_PATH, 'w'))
    print(f'Updated {updated} listings with real photo URLs')
    return len(matched)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--dry-run', action='store_true', default=True)
    args = parser.parse_args()

    execute = args.execute or '--execute' in sys.argv
    run_scrape(dry_run=not execute)
