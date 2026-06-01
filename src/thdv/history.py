import json
from typing import Any
from pathlib import Path
from datetime import datetime

from .rows import DialogRow
from .rows import MessageRow
from .rows import DialogManifestEntry


def _peer_display_name(peer: Any) -> str:
    if not isinstance(peer, dict):
        return 'UNKNOWN'

    first_name = str(peer.get('first_name') or '')
    last_name = str(peer.get('last_name') or '')
    full_name = f'{first_name} {last_name}'.strip()
    if full_name:
        return full_name

    print_name = str(peer.get('print_name') or '').strip()
    if print_name:
        return print_name

    peer_type = peer.get('peer_type')
    peer_id = peer.get('peer_id')
    if peer_type is not None and peer_id is not None:
        return f'{peer_type}#{peer_id}'

    return 'UNKNOWN'


def _payload_for_event(event: dict[str, Any]) -> Any:
    if 'text' in event:
        return event['text']
    if 'media' in event:
        return event['media']
    return event.get('action', '')


def format_message(event: dict[str, Any]) -> str:
    event_type = event.get('event')
    if event_type not in ('message', 'service'):
        return json.dumps(event, ensure_ascii=False, sort_keys=True)

    date = event.get('date')
    if isinstance(date, int | float):
        timestamp = datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
    else:
        timestamp = 'unknown time'

    from_name = _peer_display_name(event.get('from'))

    fwd_from = event.get('fwd_from')
    if isinstance(fwd_from, dict):
        fwd = f' [FWD: {_peer_display_name(fwd_from)}]'
    else:
        fwd = ''

    reply = ' [REPLY]' if event.get('reply_id') else ''
    payload = _payload_for_event(event)
    return f'[{timestamp}] {from_name}{fwd}{reply}: {payload}'


def read_json_line(line: str) -> dict[str, Any] | None:
    if not line.strip():
        return None

    event = json.loads(line)
    if not isinstance(event, dict):
        return None

    return event


def get_dialog_print_name(peer_id: str, filename: str | Path) -> str:
    path = Path(filename)
    if not path.exists():
        return 'UNKNOWN'

    with path.open(encoding='utf-8') as f:
        for line in f:
            event = read_json_line(line)
            if not event:
                continue

            for key in ('to', 'from'):
                peer = event.get(key)
                if not isinstance(peer, dict):
                    continue
                if str(peer.get('peer_id')) == peer_id:
                    return _peer_display_name(peer)

    return 'UNKNOWN'


def load_manifest_entries(manifest: str | Path) -> list[DialogManifestEntry]:
    manifest_path = Path(manifest)
    with manifest_path.open(encoding='utf-8') as f:
        data = json.load(f)

    dialogs = data.get('dialogs', {})
    if not isinstance(dialogs, dict):
        return []

    entries: list[DialogManifestEntry] = []
    for peer_id, dialog in dialogs.items():
        if not isinstance(dialog, dict):
            continue

        dumper_state = dialog.get('dumper_state')
        if not isinstance(dumper_state, dict):
            continue

        outfile = dumper_state.get('outfile')
        if not isinstance(outfile, str):
            continue

        newest_date = dialog.get('newest_date')
        if not isinstance(newest_date, int):
            newest_date = None

        entries.append(
            DialogManifestEntry(
                peer_id=str(peer_id),
                filepath=manifest_path.parent / outfile,
                newest_date=newest_date,
            )
        )

    return sorted(entries, key=lambda item: item.newest_date or 0, reverse=True)


def build_dialog_row(entry: DialogManifestEntry) -> DialogRow:
    return DialogRow(
        peer_id=entry.peer_id,
        filepath=entry.filepath,
        name=get_dialog_print_name(entry.peer_id, entry.filepath),
    )


def load_message_rows(path: str | Path) -> list[MessageRow]:
    rows: list[MessageRow] = []
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            event = read_json_line(line)
            if event:
                rows.append(MessageRow(display=format_message(event), event=event))
    return rows
