"""Headline fetcher for the morning dashboard.

Pulls a few public RSS feeds server-side (browsers can't read them directly —
none of these send CORS headers) and normalises them into small JSON records
with a thumbnail. Results are cached in memory so a dashboard left open all
day doesn't hammer the sources.
"""

import re
import json
import html
import time
import threading
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

MEDIA_NS = '{http://search.yahoo.com/mrss/}'
CONTENT_NS = '{http://purl.org/rss/1.0/modules/content/}'
UA = 'Mozilla/5.0 (compatible; MorningDashboard/1.0)'

FEEDS = {
    'us': [
        ('NBC News', 'https://feeds.nbcnews.com/nbcnews/public/news'),
        ('BBC', 'https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml'),
    ],
    'tech': [
        ('Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
        ('Engadget', 'https://www.engadget.com/rss.xml'),
        ('Wired', 'https://www.wired.com/feed/rss'),
    ],
}

PER_SECTION = 12
MAX_PER_SOURCE = 6      # so one fast-publishing outlet can't fill a card
CACHE_TTL = 600         # seconds

_cache = {'at': 0, 'data': None}
_lock = threading.Lock()

# Stock "no photo available" art some wires attach to every item.
_PLACEHOLDER = re.compile(r'(default|placeholder|logo|fallback)', re.I)
_TAGS = re.compile(r'<[^>]+>')
_IMG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)', re.I)


def _clean(text):
    if not text:
        return ''
    return html.unescape(_TAGS.sub('', text)).strip()


def _pick_image(item):
    """Best available thumbnail for an RSS <item>, or None."""
    candidates = []

    for el in item.findall(MEDIA_NS + 'thumbnail') + item.findall(MEDIA_NS + 'content'):
        url = el.get('url')
        if not url:
            continue
        medium = (el.get('medium') or el.get('type') or '')
        if medium and 'image' not in medium:
            continue
        try:
            width = int(el.get('width') or 0)
        except ValueError:
            width = 0
        candidates.append((width, url))

    for el in item.findall('enclosure'):
        url = el.get('url')
        if url and 'image' in (el.get('type') or 'image'):
            candidates.append((0, url))

    if candidates:
        # Prefer the widest tagged size; untagged (width 0) is the last resort.
        candidates.sort(key=lambda c: c[0], reverse=True)
        best = candidates[0][1]
        if not _PLACEHOLDER.search(best):
            return best

    # Some feeds only embed the image inside the description markup.
    for field in (CONTENT_NS + 'encoded', 'description'):
        blob = item.findtext(field) or ''
        match = _IMG_SRC.search(html.unescape(blob))
        if match and not _PLACEHOLDER.search(match.group(1)):
            return match.group(1)

    return None


def _published(item):
    for field in ('pubDate', 'published', 'updated'):
        raw = item.findtext(field)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).timestamp()
        except (TypeError, ValueError):
            continue
    return 0.0


def _fetch_feed(source, url):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(request, timeout=12) as response:
        root = ET.fromstring(response.read())

    items = []
    for item in root.iter('item'):
        title = _clean(item.findtext('title'))
        link = (item.findtext('link') or '').strip()
        if not title or not link:
            continue
        items.append({
            'title': title,
            'link': link,
            'source': source,
            'published': _published(item),
            'image': _pick_image(item),
            'summary': _clean(item.findtext('description'))[:180],
        })
    return items


def _merge(feeds):
    """Newest first, de-duplicated, with no single outlet running away with it."""
    collected = []
    for source, url in feeds:
        try:
            collected.extend(_fetch_feed(source, url))
        except Exception as exc:                      # one dead feed shouldn't kill the card
            print(f"[news] {source} failed: {exc}")

    collected.sort(key=lambda i: i['published'], reverse=True)

    seen, out, per_source = set(), [], {}
    for item in collected:
        key = item['title'].lower()[:70]
        if key in seen:
            continue
        if per_source.get(item['source'], 0) >= MAX_PER_SOURCE:
            continue
        seen.add(key)
        per_source[item['source']] = per_source.get(item['source'], 0) + 1
        out.append(item)
        if len(out) >= PER_SECTION:
            break
    return out


def get_headlines(force=False):
    """Cached {'us': [...], 'tech': [...], 'fetched': epoch}."""
    with _lock:
        fresh = _cache['data'] and (time.time() - _cache['at']) < CACHE_TTL
        if fresh and not force:
            return _cache['data']

        data = {section: _merge(feeds) for section, feeds in FEEDS.items()}
        data['fetched'] = time.time()

        # Keep serving the last good payload if every feed just failed.
        if not data['us'] and not data['tech'] and _cache['data']:
            return _cache['data']

        _cache['at'] = time.time()
        _cache['data'] = data
        return data


if __name__ == '__main__':
    print(json.dumps(get_headlines(), indent=2)[:3000])
