/**
 * /api/img?url=<encoded_idealista_thumb_url>
 * 
 * Proxies an Idealista thumbnail through Vercel's edge.
 * Vercel caches the response for 1 day (Cache-Control), so signed URL
 * expiry doesn't matter after the first fetch.
 * Falls back to city placeholder if upstream fails.
 */

const CITY_FALLBACKS = {
  madrid:   'https://images.unsplash.com/photo-1717703511674-58f919e0a6e1?w=800&auto=format&fit=crop&q=75',
  valencia: 'https://images.unsplash.com/photo-1649714729492-ae23e78e185d?w=800&auto=format&fit=crop&q=75',
  malaga:   'https://images.unsplash.com/photo-1612972735944-ed73dd220d21?w=800&auto=format&fit=crop&q=75',
  alicante: 'https://images.unsplash.com/photo-1663431442965-19498fc2e202?w=800&auto=format&fit=crop&q=75',
  almeria:  'https://images.unsplash.com/photo-1718133117947-94a1fe2db0a0?w=800&auto=format&fit=crop&q=75',
};

const DEFAULT_FALLBACK = CITY_FALLBACKS.malaga;

export const config = { runtime: 'edge' };

export default async function handler(req) {
  const { searchParams } = new URL(req.url);
  const url   = searchParams.get('url');
  const city  = (searchParams.get('city') || '').toLowerCase();

  if (!url) {
    const fallback = CITY_FALLBACKS[city] || DEFAULT_FALLBACK;
    return Response.redirect(fallback, 302);
  }

  // Security: only proxy img4.idealista.com URLs
  let parsed;
  try { parsed = new URL(url); } catch {
    return Response.redirect(CITY_FALLBACKS[city] || DEFAULT_FALLBACK, 302);
  }
  if (!parsed.hostname.endsWith('idealista.com')) {
    return Response.redirect(CITY_FALLBACKS[city] || DEFAULT_FALLBACK, 302);
  }

  try {
    const upstream = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.idealista.com/',
      },
      signal: AbortSignal.timeout(5000),
    });

    if (!upstream.ok || !upstream.headers.get('content-type')?.startsWith('image/')) {
      const fallback = CITY_FALLBACKS[city] || DEFAULT_FALLBACK;
      return Response.redirect(fallback, 302);
    }

    const blob = await upstream.arrayBuffer();
    return new Response(blob, {
      status: 200,
      headers: {
        'Content-Type': upstream.headers.get('content-type') || 'image/webp',
        'Cache-Control': 'public, max-age=86400, stale-while-revalidate=3600',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch {
    const fallback = CITY_FALLBACKS[city] || DEFAULT_FALLBACK;
    return Response.redirect(fallback, 302);
  }
}
