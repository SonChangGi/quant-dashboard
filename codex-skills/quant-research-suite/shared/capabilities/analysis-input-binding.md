# Capability: analysis input binding

This capability is the opt-in strict provenance contract. Do not activate it
for an ordinary application merely because a visible input changes
computation.

## Default repository-native check

On the public skill's default path, use a representative integration or E2E
check to follow the input through validation or serialization, the invoked
calculation boundary, the effective parameter, the produced result, and the
displayed or consumed result. Use a fixture where a variant has an observable
effect. This basic check does not require a manifest, A/B capture bundle, raw
trace, artifact hashes, or receipt.

## Strict compatibility contract

Activate `analysis-input-binding` only when a schema-v2 manifest declares it or
the user explicitly requests its machine-validated provenance. Its strict
assurance floor, `input_binding` gate, capture schemas, and validator behavior
remain unchanged.

Classify each control:

- `display`: presentation only;
- `result_selector`: selects an already-produced result;
- `analysis`: changes computation and result identity;
- `operation`: causes a refresh, export, publication, or other side effect.

For every `analysis` control, prove:

```text
frontend field
→ validation and canonical serialization
→ API/workflow/CLI mapping
→ authoritative parameter and effective value
→ run/result identity and artifact
→ bound UI result
```

Maintain separate draft, applied, pending, and bound state. Never display draft
values as though their results are current.

Run deterministic A/B captures. The same input twice must reproduce the core
result under an independent run identity. The variant may change only the
control's declared input pointer (plus explicitly declared allowed pointers),
and must change at least one responsible result path on a fixture where its
effect is observable.

The manifest, not the capture, owns the runtime JSON Pointers for dispatch,
applied control value, bound state, project/run identity, result hash, and
visible result values. Capture schema v2 binds:

```json
{
  "runtime_binding_contract": {
    "dispatch_input_pointer": "/request/body/config",
    "dispatch_frontend_field_pointer": "/mapping/frontend_field",
    "dispatch_canonical_field_pointer": "/mapping/canonical_field",
    "dispatch_execution_mapping_pointer": "/mapping/execution_mapping",
    "dispatch_entrypoint_sha256_pointer": "/mapping/entrypoint_sha256",
    "view_control_field_pointer": "/control/field",
    "view_applied_value_pointer": "/control/applied_value",
    "view_binding_status_pointer": "/binding/status",
    "view_project_id_pointer": "/binding/project_id",
    "view_run_id_pointer": "/binding/run_id",
    "view_result_sha256_pointer": "/binding/result_sha256",
    "view_result_values_pointer": "/binding/result_values"
  }
}
```

- the current executable project-owned UI-driver wrapper and its argv;
- baseline/repeat/variant authoritative input and result artifacts;
- each authoritative run's analysis-entrypoint hash;
- independent baseline and variant UI sessions;
- the driver's observed dispatch JSON;
- the exact result bytes adopted by the UI;
- a common bound-view JSON projection made from browser DOM, desktop
  accessibility state, mobile UI state, or another project-owned UI driver;
- the driver's raw runtime trace.

Dispatch must equal the canonical run input. Adopted result bytes must be
byte-identical to the authoritative result. The bound view must name the
manifest field, effective value, `bound` state, project/run identity, result
hash, and every declared responsible result value. Capture/session/run IDs,
artifact paths, hashes, sizes, and causal timestamps are independently checked.
Runtime artifacts must be distinct physical files from the manifest, capture,
analysis entrypoint, driver wrapper, authoritative inputs/results, and every
other runtime artifact.
The observed dispatch projection must also bind the manifest's frontend field,
canonical field, structured execution locator, and the run's entrypoint hash.
For each baseline, repeat, and variant run, capture a separate
`invocation_artifact` using
`schemas/analysis-invocation.schema.json`. Its entrypoint, input, result,
run identity, hashes, exit status, and causal timestamps must match the
authoritative run. `execution_binding.kind` is one of `argv-option`,
`json-payload`, or `config-json`: argv options are derived from the captured
argv, while JSON kinds are derived through the declared JSON Pointer from a
separate source artifact whose exact bytes, size, and hash are verified. The
captured argv must directly name the declared analysis entrypoint. A custom
free-text binding is not accepted, and coordinated manifest/dispatch echoes
cannot replace the value derived from invocation evidence. The UI dispatch
value must equal that independently derived executed value.
Every run also needs an independent `execution_trace_artifact` and a matching
command evidence item. That evidence binds the exact argv, exit code, run ID,
entrypoint/input/result hashes, trace bytes, and causal completion window.
Responsible
`result_paths` may not overlap the effective configuration or result-identity
pointers declared by the analysis capability; merely echoing an applied input,
config hash, run ID, artifact hash, or other identity metadata is not proof that
an analytical outcome changed. All JSON value comparisons are type-strict, so
booleans cannot stand in for numeric zero or one.
Each trace's command evidence must carry the exact `command_argv` declared by
the capture driver, name that driver as its source, and be checked after the
runtime phase but no later than capture generation. `command_argv[0]` must
directly execute the declared executable `runner_path`; interpreters and
framework CLIs belong inside that project-owned wrapper. An unrelated successful
command cannot attest to the trace.
Use `templates/analysis-input-binding-capture.example.json` and
`templates/analysis-invocation.example.json`.

This evidence contract is UI-runtime-neutral; it does not force React,
Playwright, a browser, an API, or any other framework. It is required only when
`analysis-input-binding` is active.

The validator proves consistency and provenance inside a locally captured
bundle. It cannot make deliberately fabricated local bytes trustworthy.
Strict/release work must therefore run the project-owned driver live, retain its
raw command traces, and have an independent reviewer compare them with the
receipt. Where adversarial local producers are in scope, add a project-specific
trusted CI, signed attestation, or hardware-backed verifier rather than claiming
that the portable local schema supplies that external trust.

Display-only changes must preserve config, command, run/result identity, and
artifact. Invalid, stale, failed, or mismatched bindings fail closed.
Completion defaults to a 24-hour maximum between capture generation and receipt
completion. A project may declare a different positive
`capability_config.analysis-input-binding.maximum_capture_age_seconds` when its
review cadence genuinely requires it; the chosen bound becomes part of the
manifest contract rather than a hidden framework assumption.

Evidence gate: `input_binding`.
