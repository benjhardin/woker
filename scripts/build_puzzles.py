"""Turn data/movies.jsonl into data/puzzles.json, the schedule the game reads.

Each day gets five movies. Woke Scores skew low (the site-wide average is
around 23), so picking uniformly would serve mostly 0-20 movies. Instead each
slot draws a verdict band with weight proportional to sqrt(band size), which
flattens the spread without making it predictable. A movie isn't repeated
until its band has been used up.

    python3 scripts/build_puzzles.py [--launch 2026-11-14] [--days 730]
"""
import argparse
import datetime
import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKERS = ['Representation Casting', 'LGBTQ+ Themes', 'Feminist Agenda', 'Racial Consciousness',
           'Climate Crusade', 'Eat the Rich', 'Body Positivity', 'Neurodivergence',
           'Revisionist History', 'Lecture Energy']
# Scheduling buckets. The site's 80-100 band only has a handful of movies, so it
# shares a bucket with 60-79 to stop those few from repeating every week.
BANDS = [(0, 19), (20, 39), (40, 59), (60, 100)]
PER_DAY = 5
MAX_PER_BAND = 3
# Lists that are recognisable on their own; Oscar winners only count from 1970 on.
MAINSTREAM = {'thematic-box-office-number-ones', 'mcu', 'studio-dc', 'studio-disney-animation',
              'disney-live-action-remakes', 'thematic-superhero', 'thematic-sequels', 'studio-a24'}
# The latest year's lists are full of small and foreign releases; only these hold up.
BIG_FRANCHISE = {'mcu', 'studio-disney-animation', 'disney-live-action-remakes'}
# Lists dominated by straight-to-video animated features.
DTV_PRONE = {'studio-dc', 'thematic-superhero'}
THEATRICAL = {'thematic-box-office-number-ones', 'thematic-oscar-winners', 'mcu',
              'studio-disney-animation', 'disney-live-action-remakes'}
EXCLUDE = set(json.load(open(os.path.join(ROOT, 'data', 'exclude.json')))) \
    if os.path.exists(os.path.join(ROOT, 'data', 'exclude.json')) else set()


def eligible(m, today):
    if m.get('score') is None or not m.get('poster') or not m.get('date') or m['slug'] in EXCLUDE:
        return False
    if m['date'] > today:
        return False
    year = int(m['date'][:4])
    lists = set(m.get('lists', []))
    if year >= int(today[:4]) and not lists & BIG_FRANCHISE:
        return False
    if 'Animation' in m.get('genres', []) and lists & DTV_PRONE and not lists & THEATRICAL:
        return False
    if lists & MAINSTREAM:
        return True
    # Pixar's list (not in MAINSTREAM) includes its shorts, so Pixar features
    # get in only through another list.
    return 'thematic-oscar-winners' in lists and year >= 1970


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--launch', default='2026-11-14')
    ap.add_argument('--days', type=int, default=730)
    ap.add_argument('--seed', default='woker')
    args = ap.parse_args()

    with open(os.path.join(ROOT, 'data', 'movies.jsonl')) as f:
        raw = [json.loads(line) for line in f]
    today = datetime.date.today().isoformat()
    pool = [m for m in raw if eligible(m, today)]

    movies, bands = {}, [[] for _ in BANDS]
    for m in pool:
        movies[m['slug']] = dict(
            slug=m['slug'], title=m['title'], year=int(m['date'][:4]), score=m['score'],
            poster=m['poster'], director=', '.join(m['director'][:2]), genres=m['genres'][:3],
            cast=m['cast'][:3], markers=[m['markers'].get(k, 0) or 0 for k in MARKERS])
        bands[next(i for i, (lo, hi) in enumerate(BANDS) if lo <= m['score'] <= hi)].append(m['slug'])

    rng = random.Random(args.seed)
    weights = [math.sqrt(len(b)) for b in bands]
    decks = [[] for _ in BANDS]

    def draw(i):
        if not decks[i]:
            decks[i] = bands[i][:]
            rng.shuffle(decks[i])
        return decks[i].pop()

    days = []
    for _ in range(args.days):
        picks, per_band, titles = [], [0] * len(BANDS), set()
        while len(picks) < PER_DAY:
            i = rng.choices(range(len(BANDS)), weights)[0]
            if per_band[i] >= MAX_PER_BAND:
                continue
            slug = draw(i)
            if movies[slug]['title'] in titles:  # e.g. two "Aladdin"s on one day
                decks[i].insert(0, slug)
                continue
            picks.append(slug)
            titles.add(movies[slug]['title'])
            per_band[i] += 1
        rng.shuffle(picks)
        days.append(picks)

    used = sorted({s for d in days for s in d})
    out = dict(launch=args.launch, movies={s: movies[s] for s in used}, days=days)
    with open(os.path.join(ROOT, 'data', 'puzzles.json'), 'w') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    print(f'{len(raw)} scraped, {len(pool)} eligible, band sizes {[len(b) for b in bands]}, '
          f'{len(days)} days written')


if __name__ == '__main__':
    main()
