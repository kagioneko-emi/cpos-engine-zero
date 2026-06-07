from __future__ import annotations

import json

import cpos.notion_zenn_bridge as bridge


def test_zenn_frontmatter_reads_published_false(tmp_path):
    article = tmp_path / 'article.md'
    article.write_text('---\ntitle: "Demo"\npublished: false\n---\n\nBody', encoding='utf-8')

    frontmatter = bridge.read_zenn_frontmatter(article)

    assert frontmatter['frontmatter_present'] is True
    assert frontmatter['title'] == 'Demo'
    assert frontmatter['published'] is False


def test_zenn_bridge_dry_run_does_not_execute_or_modify_old_helper(tmp_path):
    article = tmp_path / 'article.md'
    article.write_text('---\ntitle: "Demo"\npublished: false\n---\n\n# Body', encoding='utf-8')

    result = bridge.build_zenn_to_notion_bridge(article=article)

    assert result['schema'] == 'kagioneko.notion_zenn_bridge.v1'
    assert result['mode'] == 'dry_run'
    assert result['published'] is False
    assert result['notion_result_schema'] == 'kagioneko.notion_dry_run.v1'
    assert result['notion_url'] is None
    assert result['old_helper_modified'] is False
    assert result['old_helper_executed'] is False
    assert result['secret_values_stored'] is False
    assert 'ntn_' not in json.dumps(result)


def test_zenn_bridge_cli_dry_run(monkeypatch, tmp_path, capsys):
    article = tmp_path / 'article.md'
    article.write_text('---\ntitle: "Demo"\npublished: false\n---\n\n# Body', encoding='utf-8')
    called = {'execute': False}

    def fake_create_page(*args, **kwargs):
        called['execute'] = True
        return {'schema': 'unexpected', 'ok': False}

    monkeypatch.setattr(bridge, 'create_page', fake_create_page)

    bridge.main(['bridge', '--article', str(article), '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.notion_zenn_bridge.v1' in out
    assert '"mode": "dry_run"' in out
    assert called['execute'] is False
