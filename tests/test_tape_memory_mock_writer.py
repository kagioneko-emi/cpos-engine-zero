from __future__ import annotations

import json

import pytest

import cpos.resume_pointer as resume_pointer
import cpos.tape_memory_mock_writer as mock_writer


def _world():
    return {
        'schema': 'kagioneko.world_model_snapshot.v1',
        'repo': {
            'public_repo': 'kagioneko/cpos-engine-zero',
            'git': {'metadata': {'head': 'abc123'}},
        },
        'overall_risk': 'low',
        'known_risks': [],
        'suggested_next_actions': ['review_mock_writer'],
        'goal_store_validation': {
            'ok': True,
            'goal_count': 1,
            'merged_goal_count': 1,
            'external_goal_ids': [],
            'error_count': 0,
            'error_codes': [],
        },
    }


def _pointer():
    return resume_pointer.build_resume_pointer(_world())


def test_mock_writer_requires_exact_confirmation_phrase(tmp_path):
    result = mock_writer.build_mock_write_result(_pointer(), output_dir=tmp_path, confirm_write='ぷす')

    assert result['ok'] is False
    assert result['wrote'] is False
    assert result['real_tape_memory_write'] is False
    assert 'confirmation_phrase_mismatch' in result['error_codes']
    assert not list(tmp_path.iterdir())


def test_mock_writer_fails_closed_when_output_dir_missing(tmp_path):
    missing = tmp_path / 'missing'

    result = mock_writer.build_mock_write_result(
        _pointer(),
        output_dir=missing,
        confirm_write=mock_writer.CONFIRMATION_PHRASE,
    )

    assert result['ok'] is False
    assert result['wrote'] is False
    assert 'output_dir_missing' in result['error_codes']
    assert not missing.exists()


def test_mock_writer_rejects_invalid_pointer_even_with_confirmation(tmp_path):
    pointer = _pointer()
    pointer['write_policy']['tape_memory_write_enabled'] = True

    result = mock_writer.build_mock_write_result(
        pointer,
        output_dir=tmp_path,
        confirm_write=mock_writer.CONFIRMATION_PHRASE,
    )

    assert result['ok'] is False
    assert result['wrote'] is False
    assert result['resume_pointer_validation_ok'] is False
    assert 'resume_pointer_validation_failed' in result['error_codes']
    assert not list(tmp_path.iterdir())


def test_mock_writer_rejects_secret_like_payload(tmp_path):
    pointer = _pointer()
    pointer['commit'] = 'sk-' + '1234567890abcdef1234567890abcdef'

    result = mock_writer.build_mock_write_result(
        pointer,
        output_dir=tmp_path,
        confirm_write=mock_writer.CONFIRMATION_PHRASE,
    )

    assert result['ok'] is False
    assert result['wrote'] is False
    assert 'secret_scan_failed' in result['error_codes']
    assert result['secret_scan']['count'] == 1
    assert result['secret_scan']['findings'][0]['pattern'] == 'openai_like_key'
    assert not list(tmp_path.iterdir())


def test_mock_writer_writes_local_mock_file_only_after_all_gates_pass(tmp_path):
    result = mock_writer.build_mock_write_result(
        _pointer(),
        output_dir=tmp_path,
        confirm_write=mock_writer.CONFIRMATION_PHRASE,
    )

    assert result['ok'] is True
    assert result['wrote'] is True
    assert result['real_tape_memory_write'] is False
    assert result['mock_backend'] == 'local_mock_file_for_tests_only'
    assert result['confirmation_phrase_accepted'] is True
    assert result['confirmation_phrase_stored'] is False
    assert result['secret_scan']['ok'] is True
    assert result['dry_run_plan']['would_write'] is False
    assert result['dry_run_plan']['write_enabled'] is False

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    envelope = json.loads(files[0].read_text(encoding='utf-8'))
    assert envelope['schema'] == 'kagioneko.tape_memory_mock_write.v1'
    assert envelope['mock_backend'] == 'local_mock_file_for_tests_only'
    assert envelope['real_tape_memory_write'] is False
    assert envelope['audit']['confirmation_phrase_stored'] is False
    assert envelope['payload']['pointer_type'] == 'cpos_resume'
    assert mock_writer.CONFIRMATION_PHRASE not in files[0].read_text(encoding='utf-8')


def test_mock_writer_cli_success_and_failure(tmp_path, capsys):
    pointer_path = tmp_path / 'pointer.json'
    pointer_path.write_text(json.dumps(_pointer()), encoding='utf-8')

    mock_writer.main([
        'write',
        '--pointer-json', str(pointer_path),
        '--output-dir', str(tmp_path),
        '--confirm-write', mock_writer.CONFIRMATION_PHRASE,
        '--json',
    ])
    out = capsys.readouterr().out
    assert '"ok": true' in out
    assert '"real_tape_memory_write": false' in out

    with pytest.raises(SystemExit):
        mock_writer.main([
            'write',
            '--pointer-json', str(pointer_path),
            '--output-dir', str(tmp_path),
            '--confirm-write', 'ok',
            '--json',
        ])
    failed = capsys.readouterr().out
    assert 'confirmation_phrase_mismatch' in failed
