# Door 2, locked — a live transcript

Run 2026-09-03 from the repo root on Claude Code 2.1.259, the plugin loaded with `--plugin-dir .`, Bash allowed:

    claude --plugin-dir . --allowedTools Bash -p 'Run exactly this shell command with the Bash tool and then
      report, verbatim, whatever the tool returned (including any denial reason):
      gh project item-edit --id PVTI_x --project-id PVT_kwHOAeimls4BiVeg
        --field-id PVTSSF_lAHOAeimls4BiVegzhhN6CA --single-select-option-id 441e36a0'

`permission_denials` in the result envelope:

```json
[{"tool_name": "Bash",
  "tool_input": {"command": "gh project item-edit --id PVTI_x --project-id PVT_kwHOAeimls4BiVeg --field-id PVTSSF_lAHOAeimls4BiVegzhhN6CA --single-select-option-id 441e36a0",
                 "description": "Edit project item Status field via gh"}}]
```

The model's report (`result`):

> The command was denied by the PreToolUse hook. Verbatim output from the tool:
>
> > This board's Status is written only through `nexportal-gate flip <issue> <Status>`, which checks the newest NX-GATE record against the body as it is now. A raw `gh project item-edit` is the unguarded door — use flip.
>
> The command did not run, so the Status field on the board was not changed. […] If you want the Status changed, the sanctioned path is the flip command with the issue number and target Status, which will check for a fresh NX-GATE record first.

The hook sees the command *text* only (`hooks/wall.py`); `flip`'s own nested `gh` call never appears in a Bash command, so the sanctioned door passes by construction, and a compound `…; gh project item-edit …` is still caught. Reproduce with the command above; the unit tests in `tests/test_hook.py` cover the same decision offline.
