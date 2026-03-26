#!/usr/bin/env python3
"""
scrape-pisos.py — Scrape pisos.com for sale + rental listings across Spanish cities.

Source: pisos.com (no JS required, JSON-LD on search, HTML on detail)
Images: fotos.imghs.net CDN — permanent hotlinks, no expiry, no signing

Usage:
    python3 scripts/scrape-pisos.py [--cities all] [--limit 150] [--dry-run]

Output:
    data/pisos-raw.json — raw scraped data
    (merged into listings.json by merge-pisos.py)
"""

import urllib.request, re, json, time, sys, os, random, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, quote

BASE_DIR = Path(__file__).parent.parent
OUT_PATH  = BASE_DIR / 'data' / 'pisos-raw.json'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

CITIES = {
    # Original 5
    'madrid':    {'sale': 'pisos-madrid',     'rent': 'pisos-madrid',     'rent_path': 'alquiler'},
    'valencia':  {'sale': 'pisos-valencia',   'rent': 'pisos-valencia',   'rent_path': 'alquiler'},
    'malaga':    {'sale': 'pisos-malaga',      'rent': 'pisos-malaga',     'rent_path': 'alquiler'},
    'alicante':  {'sale': 'pisos-alicante',   'rent': 'pisos-alicante',   'rent_path': 'alquiler'},
    'almeria':   {'sale': 'pisos-almeria',    'rent': 'pisos-almeria',    'rent_path': 'alquiler'},
    # New 5
    'sevilla':   {'sale': 'pisos-sevilla',    'rent': 'pisos-sevilla',    'rent_path': 'alquiler'},
    'granada':   {'sale': 'pisos-granada',    'rent': 'pisos-granada',    'rent_path': 'alquiler'},
    'zaragoza':  {'sale': 'pisos-zaragoza',   'rent': 'pisos-zaragoza',   'rent_path': 'alquiler'},
    'murcia':    {'sale': 'pisos-murcia',     'rent': 'pisos-murcia',     'rent_path': 'alquiler'},
    'palma':     {'sale': 'pisos-palma_de_mallorca', 'rent': 'pisos-palma_de_mallorca', 'rent_path': 'alquiler'},
}

CITY_DISPLAY = {
    'madrid': 'Madrid', 'valencia': 'Valencia', 'malaga': 'Málaga',
    'alicante': 'Alicante', 'almeria': 'Almería', 'sevilla': 'Sevilla',
    'granada': 'Granada', 'zaragoza': 'Zaragoza', 'murcia': 'Murcia',
    'palma': 'Palma de Mallorca',
}

# Approx city centre lat/lng for map pins (will jitter per listing)
CITY_COORDS = {
    'madrid':   (40.4168, -3.7038), 'valencia':  (39.4699, -0.3763),
    'malaga':   (36.7213, -4.4213), 'alicante':  (38.3452, -0.4810),
    'almeria':  (36.8341, -2.4638), 'sevilla':   (37.3891, -5.9845),
    'granada':  (37.1773, -3.5986), 'zaragoza':  (41.6488, -0.8891),
    'murcia':   (37.9922, -1.1307), 'palma':     (39.5696,  2.6502),
}

# Property type mapping
PROP_TYPE_MAP = {
    'piso': 'flat', 'apartamento': 'flat', 'estudio': 'studio', 'duplex': 'duplex',
    'atico': 'penthouse', 'ático': 'penthouse', 'penthouse': 'penthouse',
    'casa': 'chalet', 'chalet': 'chalet', 'villa': 'chalet', 'adosado': 'chalet',
    'finca': 'countryHouse', 'cortijo': 'countryHouse',
    'local': 'commercial', 'oficina': 'commercial',
}

# Curated fallback photos (same as main app)
PHOTO_FALLBACKS = {
    'flat_madrid':   'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&auto=format&fit=crop&q=80',
    'flat_valencia': 'https://images.unsplash.com/photo-1560448204-603b3fc33ddc?w=800&auto=format&fit=crop&q=80',
    'flat_malaga':   'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop&q=80',
    'flat_alicante': 'https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800&auto=format&fit=crop&q=80',
    'flat_almeria':  'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&auto=format&fit=crop&q=80',
    'flat_sevilla':  'https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=800&auto=format&fit=crop&q=80',
    'flat_granada':  'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&auto=format&fit=crop&q=80',
    'flat_zaragoza': 'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=800&auto=format&fit=crop&q=80',
    'flat_murcia':   'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop&q=80',
    'flat_palma':    'https://images.unsplash.com/photo-1571055107559-3e67626fa8be?w=800&auto=format&fit=crop&q=80',
    'chalet_sevilla':'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&auto=format&fit=crop&q=80',
    'chalet_granada':'https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800&auto=format&fit=crop&q=80',
    'chalet_zaragoza':'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&auto=format&fit=crop&q=80',
    'chalet_murcia': 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop&q=80',
    'chalet_palma':  'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&auto=format&fit=crop&q=80',
    # Already-existing cities
    'chalet_madrid': 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&auto=format&fit=crop&q=80',
    'chalet_valencia':'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&auto=format&fit=crop&q=80',
    'chalet_malaga': 'https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800&auto=format&fit=crop&q=80',
    'chalet_alicante':'https://images.unsplash.com/photo-1571055107559-3e67626fa8be?w=800&auto=format&fit=crop&q=80',
    'chalet_almeria':'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&auto=format&fit=crop&q=80',
}

def get_photo_fallback(prop_type, city):
    ptype = 'flat' if prop_type in ('flat','studio','duplex','penthouse') else 'chalet'
    key = f'{ptype}_{city}'
    return PHOTO_FALLBACKS.get(key, PHOTO_FALLBACKS.get('flat_malaga', ''))

def fetch_html(url, retries=2, delay=0.3):
    """Fetch URL with retry and polite delay."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                time.sleep(delay + random.uniform(0, 0.2))
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            if attempt == retries:
                return ''
            time.sleep(1 + attempt)
    return ''

def extract_listings_from_search(html, city, operation='sale'):
    """Extract listing stubs from search page JSON-LD."""
    ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    stubs = []
    for block in ld_blocks:
        try:
            d = json.loads(block.strip())
            if d.get('@type') not in ('SingleFamilyResidence','Apartment','House',
                                       'Residence','RealEstateListing','LodgingBusiness'):
                continue
            url_path = d.get('url','')
            if not url_path or url_path.startswith('http'):
                continue
            image = d.get('image','') or d.get('photo',{}).get('contentUrl','')
            name = d.get('name','')
            # Infer property type from URL
            ptype_raw = 'flat'
            for key, val in PROP_TYPE_MAP.items():
                if key in url_path.lower() or key in name.lower():
                    ptype_raw = val
                    break
            stubs.append({
                'url_path': url_path,
                'image': image,
                'name': name,
                'city': city,
                'operation': operation,
                'property_type': ptype_raw,
            })
        except Exception:
            pass
    return stubs

def extract_detail(html, stub):
    """Extract price, rooms, size, bathrooms from detail page HTML."""
    result = dict(stub)

    # Price — find first number in 50k–20M range
    prices = re.findall(r'(\d{2,4}[.,]\d{3})', html[:200000])
    for p in prices:
        v = int(p.replace('.','').replace(',',''))
        if 30000 <= v <= 20000000:
            result['price_eur'] = v
            break

    # Rooms — ">N Hab" pattern (pisos.com specific)
    rooms_m = re.findall(r'>(\d+)\s+Hab', html[:100000], re.IGNORECASE)
    if rooms_m:
        result['rooms'] = int(rooms_m[0])

    # Size — first valid m² value
    sizes = re.findall(r'(\d+)\s*m[²2]', html[:100000])
    for s in sizes:
        v = int(s)
        if 15 <= v <= 2000:
            result['size_m2'] = v
            break

    # Bathrooms
    baths_m = re.findall(r'>(\d+)\s*(?:Ba[ñn]|ba[ñn]|wc|Aseo)', html[:100000], re.IGNORECASE)
    if baths_m:
        result['bathrooms'] = int(baths_m[0])

    # Neighborhood from URL slug
    url_parts = stub['url_path'].strip('/').split('-')
    if len(url_parts) > 1:
        # URL pattern: /comprar/piso-NEIGHBORHOOD_POSTCODE-ADID_AGENCYID/
        # Extract neighborhood from the slug part
        slug = '-'.join(url_parts[1:]).split('/')[0] if '/' in stub['url_path'] else '-'.join(url_parts[1:])
        # Remove postal code and IDs at end
        neighborhood = re.sub(r'\d{4,}.*$', '', slug).replace('-', ' ').replace('_', ' ').strip().title()
        result['neighborhood'] = neighborhood[:50] if neighborhood else None

    # Property type refine from URL
    url_lower = stub['url_path'].lower()
    for key, val in PROP_TYPE_MAP.items():
        if key in url_lower:
            result['property_type'] = val
            break

    # Listing ID from URL (the large number before the last underscore)
    id_m = re.search(r'-(\d{8,})_', stub['url_path'])
    if id_m:
        result['id'] = id_m.group(1)
    else:
        result['id'] = re.sub(r'[^a-z0-9]', '', stub['url_path'])[-20:]

    result['url'] = 'https://www.pisos.com' + stub['url_path']
    result['source'] = 'pisos.com'

    return result

def add_lat_lng(listing):
    """Add city-centred lat/lng with deterministic jitter."""
    city = listing.get('city','')
    base = CITY_COORDS.get(city)
    if not base:
        return listing
    seed = hash(str(listing.get('id','')) + city) % 10000
    import math
    angle = (seed / 10000) * 2 * math.pi
    radius = (seed % 100) / 100 * 0.04
    listing['lat'] = round(base[0] + radius * math.sin(angle), 5)
    listing['lng'] = round(base[1] + radius * math.cos(angle), 5)
    return listing

def add_investment_metrics(listing, city_medians):
    """Calculate yield, price vs median, opportunity score."""
    price = listing.get('price_eur', 0)
    size  = listing.get('size_m2', 0)
    operation = listing.get('operation','sale')

    if not price or price <= 0:
        return listing

    # Price per m²
    if size and size > 0:
        listing['price_per_m2'] = round(price / size)

    # City median
    median = city_medians.get(listing['city'], 3500)
    listing['city_median_m2'] = median
    if size and size > 0:
        ppm2 = price / size
        vs_median = round((ppm2 - median) / median * 100, 1)
        listing['price_vs_median_pct'] = vs_median

    if operation == 'sale':
        # Estimated rent from price (inverse yield calculation at city-typical cap rate)
        # Use 5% as base gross yield assumption for rent estimation
        CAP_RATES = {
            'almeria': 0.075, 'madrid': 0.055, 'valencia': 0.060,
            'alicante': 0.065, 'malaga': 0.055, 'sevilla': 0.060,
            'granada': 0.065, 'zaragoza': 0.065, 'murcia': 0.065, 'palma': 0.055,
        }
        cap = CAP_RATES.get(listing['city'], 0.060)
        est_rent = round(price * cap / 12)
        listing['estimated_rent_eur'] = est_rent
        listing['gross_yield_pct'] = round(cap * 100, 1)
        # Refine based on price vs median (cheaper = higher yield)
        if 'price_vs_median_pct' in listing:
            vs = listing['price_vs_median_pct']
            # Below median → higher yield, above → lower
            adj = -vs / 100 * 0.02  # ±2% per 100% deviation
            listing['gross_yield_pct'] = round(max(2.0, min(20.0, cap * 100 + adj * 100)), 1)
            est_rent_adj = round(price * listing['gross_yield_pct'] / 100 / 12)
            listing['estimated_rent_eur'] = est_rent_adj

        # Net yield (approx 30% cost deduction)
        listing['net_yield_pct'] = round(listing['gross_yield_pct'] * 0.70, 1)

        # Opportunity score (0-100)
        yield_score  = min(40, listing['gross_yield_pct'] * 4)  # 40pts max at 10%+
        price_score  = max(0, min(35, 35 - listing.get('price_vs_median_pct', 0) * 0.35))
        drops = listing.get('price_drops', 0) or 0
        days  = listing.get('days_on_market', 30) or 30
        momentum_score = min(25, drops * 5 + max(0, (60 - min(days, 60)) / 60 * 10))
        listing['opportunity_score'] = round(yield_score + price_score + momentum_score)

    elif operation == 'rent':
        listing['estimated_rent_eur'] = price  # price IS the monthly rent
        listing['gross_yield_pct'] = None
        listing['opportunity_score'] = 50  # neutral for rentals

    return listing

def scrape_city(city, operation, max_listings, dry_run=False):
    """Scrape one city × operation combination."""
    cfg = CITIES.get(city, {})
    if operation == 'sale':
        search_slug = cfg.get('sale', f'pisos-{city}')
        base_url = f'https://www.pisos.com/venta/{search_slug}/'
    else:
        search_slug = cfg.get('rent', f'pisos-{city}')
        base_url = f'https://www.pisos.com/alquiler/{search_slug}/'

    print(f'  [{city}/{operation}] Scraping {base_url}')
    if dry_run:
        print(f'    [DRY RUN] Would scrape up to {max_listings} listings')
        return []

    all_stubs = []
    page = 1
    while len(all_stubs) < max_listings:
        url = base_url if page == 1 else f'{base_url}{page}/'
        html = fetch_html(url)
        if not html:
            break
        stubs = extract_listings_from_search(html, city, operation)
        if not stubs:
            break
        all_stubs.extend(stubs)
        print(f'    Page {page}: +{len(stubs)} stubs (total {len(all_stubs)})')
        page += 1
        if len(stubs) < 25:  # Fewer than expected = last page
            break
        time.sleep(0.5)

    all_stubs = all_stubs[:max_listings]

    # Fetch detail pages concurrently (max 5 threads, polite)
    listings = []
    print(f'    Fetching {len(all_stubs)} detail pages...')
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {}
        for stub in all_stubs:
            detail_url = 'https://www.pisos.com' + stub['url_path']
            futures[pool.submit(fetch_html, detail_url, 2, 0.5)] = stub

        for i, future in enumerate(as_completed(futures)):
            stub = futures[future]
            try:
                html = future.result()
                if html:
                    listing = extract_detail(html, stub)
                    listing = add_lat_lng(listing)
                    if listing.get('price_eur'):
                        listings.append(listing)
            except Exception as e:
                pass
            if (i + 1) % 10 == 0:
                print(f'    ... {i+1}/{len(all_stubs)} done, {len(listings)} with price')

    print(f'  [{city}/{operation}] → {len(listings)} listings with price data')
    return listings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cities', default='new', help='all|new|existing|city1,city2')
    parser.add_argument('--limit', type=int, default=150)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--operations', default='sale,rent', help='sale|rent|sale,rent')
    args = parser.parse_args()

    if args.cities == 'all':
        target_cities = list(CITIES.keys())
    elif args.cities == 'new':
        target_cities = ['sevilla', 'granada', 'zaragoza', 'murcia', 'palma']
    elif args.cities == 'existing':
        target_cities = ['madrid', 'valencia', 'malaga', 'alicante', 'almeria']
    else:
        target_cities = [c.strip() for c in args.cities.split(',')]

    operations = [o.strip() for o in args.operations.split(',')]
    print(f'Cities: {target_cities}')
    print(f'Operations: {operations}')
    print(f'Limit per city/op: {args.limit}')
    print(f'Total target: ~{len(target_cities) * len(operations) * args.limit} listings')
    print()

    # City median price per m² (approximate, used for yield/score calculation)
    CITY_MEDIANS = {
        'madrid': 5820, 'valencia': 3238, 'malaga': 4024, 'alicante': 2508,
        'almeria': 1650, 'sevilla': 2800, 'granada': 2200, 'zaragoza': 2100,
        'murcia': 1800, 'palma': 4500,
    }

    all_listings = []
    for city in target_cities:
        for op in operations:
            listings = scrape_city(city, op, args.limit, args.dry_run)
            # Add investment metrics
            for l in listings:
                l = add_investment_metrics(l, CITY_MEDIANS)
                # Add photo fallback
                if not l.get('photo_url') or 'unsplash' in l.get('photo_url',''):
                    img = l.get('image','')
                    if img and 'imghs.net' in img:
                        l['photo_url'] = img  # Real photo from pisos.com!
                    else:
                        l['photo_url'] = get_photo_fallback(l.get('property_type','flat'), city)
            all_listings.extend(listings)

    if not args.dry_run:
        json.dump(all_listings, open(OUT_PATH, 'w'), ensure_ascii=False, indent=2)
        print(f'\nSaved {len(all_listings)} listings to {OUT_PATH}')
    else:
        print(f'\n[DRY RUN] Would have scraped ~{len(target_cities) * len(operations) * args.limit} listings')

    return all_listings

if __name__ == '__main__':
    main()
