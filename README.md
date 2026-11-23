# baby-days-out
upcoming baby events

## Checking events.json

`index.html` builds the whole site from `events.json`, so a broken file breaks the page.
Before committing a change to `events.json`, run:

```
python3 scripts/validate.py
```

It prints `OK` or lists each problem (missing fields, bad dates or times, duplicate events, banned keys).
The same check runs on GitHub for every push and pull request that touches `events.json`, and GitHub emails you if it fails.
