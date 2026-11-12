# Django cohort

Four historical issue and patch pairs were selected before reviewers received packets. The source pins list the exact selection rule, archive URLs, dataset commit and SHA-256 hashes. The only excluded intervening title concerned an authentication form. The selected pairs span Django 3.0 and 3.1 development snapshots.

## Reproduce the inputs

From the pilot directory, download the public Verified parquet file at the URL in `infra-django/source-pins.json`. Use a Python environment with PyArrow for these steps. The fetcher verifies the dataset digest and every downloaded archive. The four inputs for each executable replay are the historical base, the Haiku patch, the Sonnet patch and the maintainer fix.

```sh
python infra-django/fetch_public.py --dataset verified.parquet --cache /tmp/closing-notes-django
python infra-django/prepare_inputs.py --cache /tmp/closing-notes-django --inputs inputs --trees
```

Each archived author check is the final shell action and its following observation. In seven cases the author ran a verification script. The other ran a Django migration command on the author's temporary project. The check and note files contain the archived text. No archived author shell script is executed to prepare the packets.

## Reproduce the runtime

The independent tests used CPython 3.10.20, asgiref 3.4.1, pytz 2024.2, sqlparse 0.4.4 and psycopg2-binary 2.9.10. All 16 source trees imported their own Django version, initialized a minimal Django registry, ran a SQLite-in-memory query and imported SplitArrayField. No PostgreSQL server was required for those checks.

For each variant run a fresh Python process with `trees/<instance>/<variant>` and its `tests` directory on PYTHONPATH. Keep the maintainer patch, the source map, the prior grading outcomes and the original author labels out of blind reviewer packets.
