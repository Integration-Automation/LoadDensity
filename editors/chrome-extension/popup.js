function setStatus(text) {
  document.getElementById("status").textContent = text;
}

document.getElementById("start").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "start" }, () => {
    setStatus("Recording…");
  });
});

document.getElementById("stop").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "stop" }, (response) => {
    if (response && response.ok) {
      setStatus(`Saved ${response.count} entries`);
    } else {
      setStatus("Failed to save HAR");
    }
  });
});
