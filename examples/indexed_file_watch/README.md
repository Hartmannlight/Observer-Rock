# Indexed File Watch Example

This example demonstrates a more realistic source shape than `file_digest`:

- read a cheap discovery index from `input/index.json`
- fetch only new documents from that index by default
- use `change_tracking` to occasionally refetch a small recent-document window
- persist document history and compare newer versus older versions locally

## Layout

- `input/index.json`: newest-first discovery index
- `input/documents/*.txt`: document bodies fetched when selected
- `monitors.yml`: monitor schedule plus `change_tracking`

## Run It

```powershell
python -m observer_rock validate-workspace --workspace examples/indexed_file_watch
python -m observer_rock run-monitor indexed-file-watch --workspace examples/indexed_file_watch
python -m observer_rock query-documents --workspace examples/indexed_file_watch --profile digest_v1 --contains traffic
python -m observer_rock document-history --workspace examples/indexed_file_watch --document indexed-file-watch:meeting-2026-03-14 --profile digest_v1
```

## Simulate A New Document Plus A Rechecked Old One

1. Add a new document file under `input/documents/`.
2. Update `input/index.json` so the new document is first.
3. Edit an older document file that still sits inside the recent-document recheck window.
4. Run the monitor again.

With the shipped config, Observer Rock reads only the first discovery candidate
from the index on each run and performs one recent-document recheck every second
run. That keeps downloads bounded while still letting older but still-relevant
documents receive occasional change checks.
