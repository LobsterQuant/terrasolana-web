#!/usr/bin/env python3
"""
merge-pisos.py — Merge pisos-raw.json into the main listings.json.

- Deduplicates by listing ID
- Adds operation field ('sale'/'rent') to all listings
- Bumps cache version in HTML files
- Updates listings.json in place
"""

import json, re
from pathlib import Path

BASE = Path(__file__).parent.parent
LISTINGS_PATH = BASE / 'data' / 'listings.json'
PISOS_PATH    = BASE / 'data' / 'pisos-raw.json'

REQUIRED_FIELDS = ('id', 'city', 'price_eur', 'property_type')

def clean(l):
    """Normalise a listing to match the schema."""
    # Ensure operation field
    if 'operation' not in l:
        l['operation'] = 'sale'
    # Ensure source
    if 'source' not in l:
        l['source'] = 'idealista'
    # Ensure photo_url
    if not l.get('photo_url'):
        l['photo_url'] = ''
    # Ensure has_ booleans
    for f in ('has_elevator','has_parking','has_terrace','has_pool'):
        if f not in l:
            l[f] = False
    # Normalise city name
    l['city'] = l.get('city','').lower().strip()
    l['city_display'] = {
        'madrid':'Madrid','valencia':'Valencia','malaga':'Málaga',
        'alicante':'Alicante','almeria':'Almería','sevilla':'Sevilla',
        'granada':'Granada','zaragoza':'Zaragoza','murcia':'Murcia',
        'palma':'Palma de Mallorca',
    }.get(l['city'], l['city'].title())
    return l

def main():
    # Load existing
    existing = json.load(open(LISTINGS_PATH))
    existing_ids = {str(l['id']) for l in existing}
    print(f"Existing: {len(existing)} listings, {len(existing_ids)} unique IDs")

    # Add operation field to existing (all are sale)
    for l in existing:
        if 'operation' not in l:
            l['operation'] = 'sale'
        if 'source' not in l:
            l['source'] = 'idealista'

    # Load new pisos data
    pisos = json.load(open(PISOS_PATH))
    print(f"Pisos raw: {len(pisos)} listings")

    # Filter and clean
    added = 0
    skipped_dup = 0
    skipped_invalid = 0
    new_listings = []

    for l in pisos:
        # Check required fields
        if not all(l.get(f) for f in REQUIRED_FIELDS):
            skipped_invalid += 1
            continue
        # Deduplicate
        lid = str(l.get('id',''))
        if lid in existing_ids:
            skipped_dup += 1
            continue
        cleaned = clean(l)
        new_listings.append(cleaned)
        existing_ids.add(lid)
        added += 1

    print(f"Adding: {added} new listings")
    print(f"Skipped: {skipped_dup} duplicates, {skipped_invalid} invalid")

    # Merge
    all_listings = existing + new_listings
    print(f"Total: {len(all_listings)} listings")

    # Stats by city + operation
    from collections import defaultdict
    stats = defaultdict(lambda: defaultdict(int))
    for l in all_listings:
        stats[l.get('city','?')][l.get('operation','sale')] += 1
    print("\nCity breakdown:")
    for city in sorted(stats):
        print(f"  {city}: {dict(stats[city])}")

    # Save
    json.dump(all_listings, open(LISTINGS_PATH, 'w'), ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_listings)} listings to {LISTINGS_PATH}")

    return len(all_listings), added

if __name__ == '__main__':
    total, added = main()
