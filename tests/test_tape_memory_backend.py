from __future__ import annotations

import json

import cpos.tape_memory_backend as backend
import cpos.resume_pointer as resume_pointer


def _pointer():
    return {
        'schema': resume_pointer.POINTER_SCHEMA,
        'pointer_type': 'cpos_resume',
        'commit': 'abc123',
        'repo': 'kagioneko/cpos-engine-zero',
    }


def _validation(ok: bool = True):
    return {
        'schema': resume_pointer.VALIDATION_SCHEMA,
        'ok': ok,
    }


def _secret_scan(ok: bool = True, count: int = 0):
    return {
        'ok': ok,
        'count': count,
        'findings': [],
    }


def _target():
    return {
        'backend': 'in_memory_fake',
        'system': 'tape-memory',
        'record_type': 'cpos_resume_pointer',
        'path_or_key': 'test://tape-memory/resume-pointer',
    }


def _confirmation(accepted: bool = True, phrase: str = backend.CONFIRMATION_PHRASE):
    return {
        'accepted': accepted,
        'phrase': phrase,
    }


def _audit():
    return {
        'metadata_only': True,
        'raw_payload_echoed': False,
    }


def test_backend_protocol_accepts_fake_backend_instance():
    fake = backend.InMemoryTapeMemoryBackend()
    assert isinstance(fake, backend.TapeMemoryBackendProtocol)


def test_backend_validation_passes_for_metadata_only_fake_request():
    result = backend.validate_backend_write_request(
        pointer=_pointer(),
        validation=_validation(),
        secret_scan=_secret_scan(),
        target=_target(),
        confirmation=_confirmation(),
        audit=_audit(),
    )

    assert result['schema'] == 'kagioneko.tape_memory_backend_fake.v1'
    assert result['ok'] is True
    assert result['error_count'] == 0
    assert result['backend'] == 'in_memory_fake'
    assert result['real_tape_memory_write'] is False
    assert result['metadata_only'] is True


def test_backend_validation_rejects_bad_confirmation_and_secret_scan():
    result = backend.validate_backend_write_request(
        pointer=_pointer(),
        validation=_validation(),
        secret_scan=_secret_scan(ok=False, count=1),
        target=_target(),
        confirmation=_confirmation(accepted=False, phrase='ぷす'),
        audit=_audit(),
    )

    assert result['ok'] is False
    assert 'confirmation_missing' in result['error_codes']
    assert 'confirmation_mismatch' in result['error_codes']
    assert 'secret_scan_failed' in result['error_codes']
    assert 'secret_scan_nonzero' in result['error_codes']


def test_in_memory_fake_backend_records_only_on_success():
    fake = backend.InMemoryTapeMemoryBackend()

    envelope = fake.write_resume_pointer(
        pointer=_pointer(),
        validation=_validation(),
        secret_scan=_secret_scan(),
        target=_target(),
        confirmation=_confirmation(),
        audit=_audit(),
    )

    assert envelope['ok'] is True
    assert envelope['backend'] == 'in_memory_fake'
    assert envelope['real_tape_memory_write'] is False
    assert envelope['metadata_only'] is True
    assert envelope['validation_ok'] is True
    assert envelope['secret_scan_ok'] is True
    assert len(fake.writes) == 1
    stored = fake.writes[0]
    assert stored['target']['backend'] == 'in_memory_fake'
    assert stored['audit']['confirmation_phrase_stored'] is False
    assert backend.CONFIRMATION_PHRASE not in json.dumps(stored, ensure_ascii=False)
    assert 'abc123' not in json.dumps(stored, ensure_ascii=False)


def test_in_memory_fake_backend_does_not_record_failed_writes():
    fake = backend.InMemoryTapeMemoryBackend()

    envelope = fake.write_resume_pointer(
        pointer=_pointer(),
        validation=_validation(ok=False),
        secret_scan=_secret_scan(ok=False, count=1),
        target={**_target(), 'backend': 'wrong'},
        confirmation=_confirmation(accepted=False, phrase='ok'),
        audit={'metadata_only': False, 'raw_payload_echoed': True},
    )

    assert envelope['ok'] is False
    assert fake.writes == []
    assert 'invalid_backend' in envelope['error_codes']
    assert 'validation_failed' in envelope['error_codes']
    assert 'secret_scan_failed' in envelope['error_codes']
    assert 'confirmation_mismatch' in envelope['error_codes']


def test_backend_cli_inspect_json(capsys):
    backend.main(['inspect', '--json'])
    out = capsys.readouterr().out
    assert 'kagioneko.tape_memory_backend_fake.v1' in out
    assert 'in_memory_fake' in out
    assert 'TapeMemoryBackendProtocol' in out
