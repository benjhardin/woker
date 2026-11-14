"""Fetch movie scores from wokemoviescore.com into data/movies.jsonl.

Collects movie slugs from a handful of the site's list pages (chosen to favour
recognisable films), then reads each movie page's JSON-LD block, which carries
the Woke Score, the ten marker scores, poster, cast and so on.

Resumable: movies already in the output file are skipped.

    python3 scripts/scrape.py
"""
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'movies.jsonl')
BASE = 'https://wokemoviescore.com'
LISTS = [
    'thematic-box-office-number-ones', 'thematic-oscar-winners', 'studio-pixar',
    'studio-disney-animation', 'mcu', 'thematic-superhero', 'studio-dc',
    'thematic-sequels', 'disney-live-action-remakes', 'studio-a24',
]
DELAY = 0.25  # be polite


def get(url):
    return subprocess.run(['curl', '-sL', '--max-time', '20', '-A', 'Mozilla/5.0 (Woker game)', url],
                          capture_output=True, check=True).stdout.decode('utf-8', 'replace')


def parse_movie(slug, html):
    movie = None
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        d = json.loads(blob)
        for n in d.get('@graph', [d]):
            if n.get('@type') == 'Movie':
                movie = n
    if not movie:
        return None
    props = {p['name']: p.get('value') for p in movie.get('additionalProperty', [])}
    score = props.pop('Woke Score', None)
    return dict(slug=slug, title=movie.get('name'), date=movie.get('datePublished'),
                poster=movie.get('image'), genres=movie.get('genre', []),
                director=[p['name'] for p in movie.get('director', [])],
                cast=[p['name'] for p in movie.get('actor', [])][:4],
                tmdb=movie.get('sameAs'), score=score, markers=props)


def main():
    sources = {}
    for name in LISTS:
        html = get(f'{BASE}/list/{name}/')
        for slug in re.findall(r'href="/movie/([^"/]+)/"', html):
            sources.setdefault(slug, set()).add(name)
        time.sleep(DELAY)

    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            done = {json.loads(line)['slug'] for line in f}
    todo = [s for s in sources if s not in done]
    print(f'{len(sources)} slugs, {len(todo)} to fetch', flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'a') as fo:
        for i, slug in enumerate(todo):
            try:
                rec = parse_movie(slug, get(f'{BASE}/movie/{slug}/'))
                if rec:
                    rec['lists'] = sorted(sources[slug])
                    fo.write(json.dumps(rec) + '\n')
                    fo.flush()
                else:
                    print('no movie data', slug, file=sys.stderr)
            except Exception as e:
                print('error', slug, e, file=sys.stderr)
            if i % 100 == 0:
                print(i, flush=True)
            time.sleep(DELAY)


if __name__ == '__main__':
    main()
