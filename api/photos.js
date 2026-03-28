/**
 * /api/photos?url=<encoded_pisos_url>
 *
 * Fetches a pisos.com listing page and extracts up to 4 gallery images.
 * Returns JSON: { photos: ["url1", "url2", ...] }
 * Only works for pisos.com — idealista listings don't expose multi-photo.
 * Cached at edge for 24h.
 */

export const config = { runtime: 'edge' };

export default async function handler(req) {
  const { searchParams } = new URL(req.url);
  const listingUrl = searchParams.get('url');

  const corsHeaders = {
    'Access-Control-Allow-Origin': 'https://terrasolana.com',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=86400, stale-while-revalidate=3600',
  };

  if (!listingUrl) {
    return new Response(JSON.stringify({ photos: [] }), { headers: corsHeaders });
  }

  // Only allow pisos.com
  let parsed;
  try { parsed = new URL(listingUrl); } catch {
    return new Response(JSON.stringify({ photos: [] }), { headers: corsHeaders });
  }
  if (!parsed.hostname.endsWith('pisos.com')) {
    return new Response(JSON.stringify({ photos: [] }), { headers: corsHeaders });
  }

  try {
    const res = await fetch(listingUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://www.pisos.com/',
      },
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      return new Response(JSON.stringify({ photos: [] }), { headers: corsHeaders });
    }

    const html = await res.text();

    // Extract fchm-wp thumbnail URLs (unique, deduplicated, up to 4)
    const pattern = /https:\/\/fotos\.imghs\.net\/fchm-wp\/[^\s"'<>]+\.jpg/g;
    const matches = [...html.matchAll(pattern)].map(m => m[0]);
    // Deduplicate while preserving order
    const seen = new Set();
    const unique = [];
    for (const u of matches) {
      if (!seen.has(u)) {
        seen.add(u);
        unique.push(u);
        if (unique.length >= 4) break;
      }
    }

    // Convert thumbnails to full-size by swapping fchm-wp → fch-wp
    const fullSize = unique.map(u => u.replace('/fchm-wp/', '/fch-wp/'));

    return new Response(JSON.stringify({ photos: fullSize }), { headers: corsHeaders });

  } catch {
    return new Response(JSON.stringify({ photos: [] }), { headers: corsHeaders });
  }
}
