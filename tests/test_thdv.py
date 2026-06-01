import json
from typing import Any
from pathlib import Path
from datetime import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtCore import QCoreApplication

from thdv import DialogRow
from thdv import MessageRow
from thdv import DialogListModel
from thdv import MessageListModel
from thdv import format_message
from thdv import load_message_rows
from thdv import get_dialog_print_name
from thdv import load_manifest_entries


@pytest.fixture(scope='session', autouse=True)
def qcore_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        ''.join(f'{json.dumps(row, ensure_ascii=False)}\n' for row in rows),
        encoding='utf-8',
    )


def test_format_message_handles_forward_reply_and_names() -> None:
    timestamp = 1_779_220_321
    event = {
        'event': 'message',
        'date': timestamp,
        'from': {'first_name': 'Alice', 'last_name': 'Smith'},
        'fwd_from': {'first_name': 'Bob', 'last_name': 'Jones'},
        'reply_id': '42',
        'text': 'hello',
    }

    formatted = format_message(event)

    rendered_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    assert formatted == f'[{rendered_time}] Alice Smith [FWD: Bob Jones] [REPLY]: hello'


def test_format_message_uses_peer_fallback_and_media_payload() -> None:
    event = {
        'event': 'message',
        'date': 1_779_220_321,
        'from': {'peer_type': 'user', 'peer_id': 123},
        'media': {'type': 'photo', 'caption': ''},
    }

    formatted = format_message(event)

    assert 'user#123' in formatted
    assert "'type': 'photo'" in formatted


def test_format_message_serializes_unknown_events() -> None:
    formatted = format_message({'event': 'other', 'value': 3})

    assert json.loads(formatted) == {'event': 'other', 'value': 3}


def test_get_dialog_print_name_prefers_print_name(tmp_path: Path) -> None:
    path = tmp_path / 'dialog.jsonl'
    write_jsonl(
        path,
        [
            {
                'event': 'message',
                'from': {'peer_id': 10, 'print_name': 'Someone'},
                'to': {'peer_id': 20, 'print_name': 'Target Chat'},
            }
        ],
    )

    assert get_dialog_print_name('20', path) == 'Target Chat'


def test_get_dialog_print_name_falls_back_to_peer_id(tmp_path: Path) -> None:
    path = tmp_path / 'dialog.jsonl'
    write_jsonl(
        path,
        [
            {
                'event': 'message',
                'from': {'peer_id': 99, 'peer_type': 'channel'},
                'to': {'peer_id': 1, 'print_name': 'Me'},
            }
        ],
    )

    assert get_dialog_print_name('99', path) == 'channel#99'


def test_get_dialog_print_name_handles_empty_and_missing_match(tmp_path: Path) -> None:
    empty = tmp_path / 'empty.jsonl'
    empty.write_text('', encoding='utf-8')
    missing = tmp_path / 'missing.jsonl'
    write_jsonl(missing, [{'event': 'message', 'from': {'peer_id': 1}, 'to': {'peer_id': 2}}])

    assert get_dialog_print_name('123', empty) == 'UNKNOWN'
    assert get_dialog_print_name('123', missing) == 'UNKNOWN'


def test_load_manifest_entries_sorts_by_newest_date(tmp_path: Path) -> None:
    manifest = tmp_path / 'progress.json'
    manifest.write_text(
        json.dumps(
            {
                'dialogs': {
                    'old': {'newest_date': 10, 'dumper_state': {'outfile': 'json/old.jsonl'}},
                    'new': {'newest_date': 30, 'dumper_state': {'outfile': 'json/new.jsonl'}},
                    'unknown': {'newest_date': None, 'dumper_state': {'outfile': 'json/unknown.jsonl'}},
                }
            }
        ),
        encoding='utf-8',
    )

    entries = load_manifest_entries(manifest)

    assert [entry.peer_id for entry in entries] == ['new', 'old', 'unknown']
    assert entries[0].filepath == tmp_path / 'json/new.jsonl'


def test_load_message_rows_ignores_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / 'messages.jsonl'
    event = {
        'event': 'message',
        'date': 1_779_220_321,
        'from': {'print_name': 'Sender'},
        'text': 'hello',
    }
    path.write_text(f'\n{json.dumps(event)}\n\n', encoding='utf-8')

    rows = load_message_rows(path)

    assert len(rows) == 1
    assert rows[0].event == event
    assert 'Sender' in rows[0].display


def test_message_model_ignores_stale_generation() -> None:
    model = MessageListModel()
    stale = [MessageRow(display='stale', event={'event': 'message'})]
    current = [MessageRow(display='current', event={'event': 'message'})]

    model.reset_for_generation(2)

    assert not model.append_rows(1, stale)
    assert model.rowCount() == 0
    assert model.append_rows(2, current)
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == 'current'


def test_dialog_model_ignores_stale_generation() -> None:
    model = DialogListModel()
    stale = [DialogRow(peer_id='1', filepath=Path('stale.jsonl'), name='stale')]
    current = [DialogRow(peer_id='2', filepath=Path('current.jsonl'), name='current')]

    model.reset_for_generation(2, total=1)

    assert not model.append_rows(1, stale)
    assert model.rowCount() == 0
    assert model.append_rows(2, current)
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == 'current'
