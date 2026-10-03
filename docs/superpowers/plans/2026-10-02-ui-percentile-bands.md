# UI and percentile band implementation plan

Execute in the existing isolated feature worktree under the approved roadmap.

## Shared statistical windows

- [x] Add a pure statistics helper that merges success/failure samples, prefers epoch start_time, sorts observations, and creates bounded time buckets. Exclude missing/invalid latency measurements, retain request counts, and represent empty latency windows as null.
- [x] Use the approved rounded-order-statistic rule for p50/p95/p99 window charts. Preserve the existing summary report's linear interpolation and keys for consumers; explicitly document this existing aggregate/window distinction.
- [x] Verify unsorted records, failure samples, zero timestamps, gaps, singleton windows, non-unit bucket durations and bounded history.

## Offline and live charts

- [x] Render a p50 line, p50–p95 and p95–p99 fill_between bands for offline reports, with a separate RPS chart. Preserve report filenames and return keys.
- [x] Replace mixed Qt axes with separate latency/RPS charts and Qt area series; bound histories and leave gaps disconnected.
- [x] Extend dashboard JSON/SSE with bounded chart windows, responsive SVG bands, failure rate and percentile cards; preserve existing snapshot keys and render dynamic names with text nodes.

## GUI lifecycle and installed wheel smoke

- [ ] Inspect and redesign existing GUI into settings/run controls, metrics/charts and results/logs/history. Preserve language and script loading.
- [ ] Make Start/Stop states explicit; background execution emits Qt signals only, failures/completion retain results, cancellation cleans up runner/client/thread.
- [ ] Extend offscreen installed-wheel GUI probe with real execution and cancellation; verify Qt/widget lifecycle, dashboard SSE concurrency and safe dynamic content.
- [x] Run focused and full checks for this batch, update three README languages/Sphinx/architecture and outstanding ledger, review, commit and push.

## User-requested stopping boundary

On 2026-10-02 the user requested finishing the current batch, committing it and
removing completed progress items, then stopping. The shared bands, responsive
browser dashboard and existing native worker-health work are the current batch.
Full desktop controls/Start-Stop/action-file redesign and execution/cancellation
installed-wheel GUI smoke remain in progress.md #18/#24. Async engine parity and
shared functional/load/synthetic scripts are also deferred; no new implementation
for those domains was started after the stopping request.

The browser UI was verified in headless Edge at desktop (1440px) and mobile
(390px) widths with real SSE, disconnected latency gaps, text-only malicious
request names, no JavaScript errors and no horizontal overflow. The installed
charts probe now renders actual LoadDensity report PNGs. Protocol event start
timestamps are converted from monotonic duration clocks to epoch time. Summary
latency filtering and scaled means preserve finite dashboard JSON and counts.

Final batch verification: 1442 passed, 14 optional skips and four existing
warnings; Ruff E/F/W/C90/I passed. Six subprocess smoke tests passed both from
the checkout and from the rebuilt installed wheel in a network-disabled Docker
container. The Docker runtime user now has a real writable home, addressing
qt-material theme generation under an unprivileged account. On 2026-10-03 all
48 updated extras cells and the Compose service job passed (run37006974442).
