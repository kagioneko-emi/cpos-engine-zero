from pathlib import Path


def test_redis_rate_limit_docs_do_not_embed_credentials():
    guide = Path('deploy/hardened/REDIS_RATE_LIMIT_GUIDE.md').read_text(encoding='utf-8')
    env = Path('deploy/hardened/hardened.env.example').read_text(encoding='utf-8')
    assert 'CPOS_RATE_LIMIT_REDIS_URL_FILE' in guide
    assert 'CPOS_RATE_LIMIT_REDIS_URL_FILE' in env
    assert 'redis://user:password' not in guide
    assert 'redis://user:password' not in env
    assert '/run/secrets/cpos_redis_rate_limit_url' in guide
