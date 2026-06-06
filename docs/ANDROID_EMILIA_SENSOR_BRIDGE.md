# Android Emilia Sensor Bridge — Draft

This is a documentation-only bridge note for connecting Android Emilia to the Kagioneko Cognitive Agent OS.

It does not implement Android integration and does not read private phone data.

## Local reference points

Reference categories:

- Android app repository path, supplied explicitly by the operator
- VPS receiver file path, supplied explicitly by the operator
- public article path, supplied explicitly by the operator

Concrete local paths belong in the private lab repo or local handoff notes, not in public defaults. These references are treated as external/experimental sources. CPOS should observe metadata only unless explicitly reviewed.

## Why this matters

Android Emilia is a candidate physical/life-context sensor layer:

- accelerometer / shake
- light level
- battery and charging state
- audio level
- barometer / pressure
- steps or motion
- app-local NeuroState summaries
- diary/event presence

This can make the repo-family Cognitive Agent OS more embodied, but it also raises privacy and action-boundary risks.

## Safe initial posture

Initial CPOS integration should be observe-only:

- no phone control
- no microphone/camera content ingestion
- no raw diary text persistence by CPOS
- no secret/token ingestion
- no automatic upload/publish/video pipeline trigger
- no automatic notification or background action
- no location collection unless separately designed and explicitly approved

Allowed first metadata examples:

```json
{
  "schema": "kagioneko.sensor_event.v1",
  "source": "android_emilia",
  "event_type": "android_emilia_status_observed",
  "summary": "Android Emilia bridge reference exists; integration not enabled",
  "risk": "medium",
  "metadata_only": true,
  "raw_outputs_stored": false,
  "secret_values_stored": false,
  "execute_automatically": false
}
```

## Candidate event types

- `android_emilia_bridge_detected`
- `android_emilia_status_observed`
- `android_emilia_sensor_summary_available`
- `android_emilia_diary_summary_available`
- `android_emilia_privacy_review_required`
- `android_emilia_action_boundary_required`

## Privacy notes

Android sensors are closer to the user's body and environment than repo sensors.

Therefore:

- raw sensor streams should not be stored in CPOS by default
- diary text should remain outside CPOS unless manually summarized/redacted
- receiver secrets must stay in Vault or environment-managed runtime, never docs/code
- publish/upload actions require Human Escalation and explicit confirmation

## Recommended path

1. Finish read-only Git/Time sensor MVP.
2. Add an Android Emilia inventory sensor that only reports whether the bridge references exist.
3. Define a redacted Android Emilia event schema.
4. Review privacy and action boundaries.
5. Only then consider ingesting coarse summaries.

Recommended first implementation, if approved later:

```text
cpos/sensors/android_emilia_sensor.py
```

The first implementation should only check local reference paths and emit metadata about bridge availability.
