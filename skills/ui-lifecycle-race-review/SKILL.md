---
name: ui-lifecycle-race-review
description: Finds UI lifecycle races where delayed effects, timers, RAF, observers, or callbacks outlive the view that owns them.
license: MIT
---

# UI Lifecycle Race Review

Standalone, read-only frontend lifecycle/timing review.

## INVARIANT

> **Work scheduled by one view generation must not act after that view, interaction, or DOM target has been replaced.**

## HUNT

Hunt for:
- effects and cleanup;
- setTimeout/setInterval, RAF, microtasks;
- ResizeObserver/MutationObserver;
- focus, scroll, measurement, refs;
- debounce/throttle, transitions, Suspense/concurrent rendering;
- navigation or selection replacement while callbacks are queued.

## PROVE

Trace `view A schedules → view B replaces A → callback A runs`. Identify the view/interaction identity, the actual changed state or DOM effect, and whether the callback cancels or revalidates before that effect. Inspect the framework's actual scheduling/cleanup contract and captured versus current refs; do not assume unmount, cleanup registration, or a reused DOM node proves the callback cannot act.

Show a supported replacement trigger and an observable wrong effect. A queued callback that is harmless, targets a still-valid independent owner, or is rejected before mutation is a safe control, not a race finding.

## DO NOT REPORT

Do not report timers merely because they exist. Do not treat a delayed frame as an ownership mechanism. If the defect is general async stale-state rather than UI lifecycle, use `stale-work-race-review`.

## PREFER

Cancel scheduled work or validate exact view, route, selection, interaction, and DOM target identity before effects.

## OUTPUT

Return `# UI Lifecycle Race Review` with inspected scheduling/cleanup paths, proved lifecycle races, unresolved leads, safe guards, and deterministic tests. Include scheduled work, owner identity, replacement event, late effect, and fix; separate source reasoning from executed reproduction.

Use `FINDING` for a demonstrated wrong late effect; `CLEAN` requires all material scheduling, replacement, and effect paths in the declared scope to be inspected. Use `LEAVE ALONE` for a positively safe suspected callback, or `INSUFFICIENT EVIDENCE` when its lifecycle/framework contract is missing and no violation is established.
