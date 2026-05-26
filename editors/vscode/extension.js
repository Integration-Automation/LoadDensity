const { workspace, window } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const config = workspace.getConfiguration("loaddensity");
  const command = config.get("python", "python");
  const args = config.get("lspArgs", ["-m", "je_load_density.action_lsp"]);

  const serverOptions = {
    run:   { command, args, transport: TransportKind.stdio },
    debug: { command, args, transport: TransportKind.stdio },
  };

  const clientOptions = {
    documentSelector: [
      { scheme: "file", language: "json" },
      { scheme: "file", language: "loaddensity-action" },
    ],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.{json,action.json}"),
    },
  };

  client = new LanguageClient(
    "loaddensity",
    "LoadDensity Action JSON",
    serverOptions,
    clientOptions,
  );

  client.start().catch((error) => {
    window.showErrorMessage(
      `LoadDensity LSP failed to start. Is je_load_density installed for "${command}"? (${error})`,
    );
  });

  context.subscriptions.push(client);
}

function deactivate() {
  if (!client) return undefined;
  return client.stop();
}

module.exports = { activate, deactivate };
