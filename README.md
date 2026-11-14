# Woker

A daily parody guessing game: five movies a day, guess the Woke Score that
[Woke Movie Score](https://wokemoviescore.com/)'s "Consciousness Algorithm" gave
each one. Up to 1,000 points per movie, Wordle-style emoji share grid, streaks
and stats kept in the browser.

## Run it

```bash
python3 -m http.server 8417
```

Then open http://localhost:8417. It's a static site (`index.html` + `data/puzzles.json`),
so any static host works (GitHub Pages, Netlify, Cloudflare Pages, Vercel).

Add `?day=N` to replay an earlier puzzle as practice; it doesn't touch stats.
Future days can't be opened this way.

## Data

```bash
python3 scripts/scrape.py          # refresh data/movies.jsonl (resumable, polite delay)
python3 scripts/build_puzzles.py   # rebuild data/puzzles.json
```

- `scrape.py` pulls movie slugs from a set of the site's list pages (box-office
  #1s, Oscar winners, Disney/Pixar/Marvel/DC, etc.) and reads the JSON-LD on each
  movie page.
- `build_puzzles.py` filters to recognisable, released films and lays out a
  schedule from `--launch` (default 2026-11-14). Scores skew low, so each slot
  draws a verdict band weighted by sqrt(band size) to get a better spread.
- Add slugs to `data/exclude.json` (a JSON array) to drop movies from the pool.

Puzzle #1 is the launch date; the game picks the day from the player's local date.
Rebuilding with the same seed and data keeps past days stable. Adding new
movies reshuffles future days, so pin `--launch` and treat already-played days as
fixed if that matters.
