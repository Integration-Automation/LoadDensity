# LoadDensity Action JSON — VS Code

Companion extension that connects to the LoadDensity LSP server
(`python -m je_load_density.action_lsp`) and provides:

* Completion for every registered `LD_*` command.
* Inline lint diagnostics (`textDocument/publishDiagnostics`) on every
  change.
* JSON Schema validation for files matching `*.action.json` via the
  bundled schema (`schemas/loaddensity-action-schema.json`).

## Build locally

```bash
cd editors/vscode
npm install
npm run package         # produces a .vsix
code --install-extension loaddensity-0.1.0.vsix
```

Generate the bundled schema once with:

```bash
python -c "from je_load_density import export_schema; \
  export_schema('editors/vscode/schemas/loaddensity-action-schema.json')"
```

## Configuration

`loaddensity.python` — Python interpreter that launches the LSP. Defaults
to whatever `python` is on `PATH`.

`loaddensity.lspArgs` — Args passed to that interpreter. Defaults to
`["-m", "je_load_density.action_lsp"]`.

## Requirements

* The `je_load_density` Python package importable from the configured
  interpreter.
* VS Code 1.85+.
