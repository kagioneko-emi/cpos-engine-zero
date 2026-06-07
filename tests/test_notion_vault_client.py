from __future__ import annotations

import json

import cpos.notion_vault_client as notion


def test_notion_dry_run_uses_vault_placeholders_without_values(tmp_path):
    source = tmp_path / 'summary.md'
    source.write_text('# Title\n\n- item\n\n```\ncode\n```\n', encoding='utf-8')

    result = notion.dry_run_page(title='Demo', source=source)

    assert result['schema'] == 'kagioneko.notion_dry_run.v1'
    assert result['ok'] is True
    assert result['execute_required'] is True
    assert result['vault_required'] is True
    assert result['database_id_source'] == 'vault:secret/notion#memo_db_id'
    assert result['token_source'] == 'vault:secret/notion#api_key'
    assert result['secrets_printed'] is False
    assert result['secret_values_stored'] is False
    assert 'ntn_' not in json.dumps(result)


def test_build_page_payload_is_markdown_based_and_secret_free(tmp_path):
    payload = notion.build_page_payload(title='Demo', markdown='# H\n\nText')

    assert payload['schema'] == 'kagioneko.notion_page_payload.v1'
    assert payload['vault_required'] is True
    assert payload['notion_payload']['parent']['database_id'] == 'vault:secret/notion#memo_db_id'
    assert payload['notion_payload']['children'][0]['type'] == 'heading_1'
    assert payload['secret_values_stored'] is False


def test_notion_cli_dry_run_does_not_require_vault(monkeypatch, tmp_path, capsys):
    source = tmp_path / 'summary.md'
    source.write_text('# Demo', encoding='utf-8')
    called = {'vault': False}

    def fake_vault(*args, **kwargs):
        called['vault'] = True
        return 'should-not-be-called'

    monkeypatch.setattr(notion, 'vault_field', fake_vault)

    notion.main(['page', '--source', str(source), '--title', 'Demo', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.notion_dry_run.v1' in out
    assert 'ntn_' not in out
    assert called['vault'] is False
