// LoadDensity Recorder — background service worker.
// Captures request + response metadata via chrome.webRequest, batches
// them into a HAR-shaped object, and emits a downloadable JSON.
/* global chrome */

// "<all_urls>" is Chrome's match pattern for every URL, not HTML.
// eslint-disable-next-line xss/no-mixed-html
const ALL_URLS = { urls: ["<all_urls>"] };

const state = {
  recording: false,
  entries: new Map(),
  output: [],
};

function nowIso() {
  return new Date().toISOString();
}

function onBeforeRequest(details) {
  if (!state.recording) return;
  state.entries.set(details.requestId, {
    startedDateTime: nowIso(),
    request: {
      method: details.method,
      url: details.url,
      headers: [],
      postData: details.requestBody
        ? { text: JSON.stringify(details.requestBody) }
        : undefined,
    },
  });
}

function onSendHeaders(details) {
  const entry = state.entries.get(details.requestId);
  if (!entry) return;
  entry.request.headers = (details.requestHeaders || []).map(({ name, value }) => ({
    name, value,
  }));
}

function onCompleted(details) {
  if (!state.recording) return;
  const entry = state.entries.get(details.requestId);
  if (!entry) return;
  entry.response = {
    status: details.statusCode,
    statusText: details.statusLine || "",
    headers: (details.responseHeaders || []).map(({ name, value }) => ({
      name, value,
    })),
    content: { size: 0, mimeType: "" },
  };
  entry.time = Date.now() - new Date(entry.startedDateTime).getTime();
  state.output.push(entry);
  state.entries.delete(details.requestId);
}

chrome.webRequest.onBeforeRequest.addListener(onBeforeRequest, ALL_URLS, ["requestBody"]);
chrome.webRequest.onSendHeaders.addListener(onSendHeaders, ALL_URLS, ["requestHeaders"]);
chrome.webRequest.onCompleted.addListener(onCompleted, ALL_URLS, ["responseHeaders"]);

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "start") {
    state.output = [];
    state.entries.clear();
    state.recording = true;
    sendResponse({ ok: true });
  } else if (message.type === "stop") {
    state.recording = false;
    const har = {
      log: {
        version: "1.2",
        creator: { name: "loaddensity-recorder", version: "0.1.0" },
        entries: state.output,
      },
    };
    // A Manifest V3 service worker has no URL.createObjectURL, so the HAR goes out as a data URL.
    const url = "data:application/json;charset=utf-8," + encodeURIComponent(JSON.stringify(har, null, 2));
    chrome.downloads.download({
      url, filename: `loaddensity-${Date.now()}.har`, saveAs: true,
    });
    sendResponse({ ok: true, count: state.output.length });
  }
  return true;
});
