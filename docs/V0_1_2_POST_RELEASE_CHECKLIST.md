# CPOS Engine-Zero v0.1.2 Post-release Checklist

Date: 2026-06-08

## Purpose

A short checklist for the post-release period immediately after the `v0.1.2` release.
This is not a release authority and does not authorize publication, deployment,
credential rotation, or any real tape-memory write.

## Keep as-is

- Keep the Zenn article as `published: false` unless explicit publication is requested.
- Keep the Notion summary aligned with the Zenn wording.
- Keep the README links pointing to the v0.1.2 release / runbook / summaries.
- Keep real tape-memory writes disabled.
- Keep the test-only mock writer test-only.
- Keep AGI-completion language out of public-facing copy.

## Confirm after release

- GitHub Release URL is correct.
- The release notes and GitHub draft match the shipped theme.
- The post-release summary is consistent with the Zenn and Notion summaries.
- The readiness review remains available as the safety baseline.
- `prepublish_check` and `release_check` remain the reference checks for future edits.

## Do not do yet

- Do not enable a real tape-memory backend.
- Do not treat ぷす, `ok`, or `go` as approval for memory writes.
- Do not rotate credentials unless there is a separate explicit instruction.
- Do not publish Zenn or Notion just because the GitHub release exists.
- Do not add new release tags without the explicit final release phrase.

## When the user returns, the next decisions are usually:

1. Whether to keep Zenn as draft or publish it.
2. Whether to keep the Notion summary as-is or expand it.
3. Whether to leave tape-memory backend work parked.

- `cpos.tape_memory_backend.py` is test-only and fake-backed; do not treat it as a real backend.
