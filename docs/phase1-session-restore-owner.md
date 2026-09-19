# Phase 1 session restore ownership

The hosted private beta has exactly one provider-facing restore owner: `mobile_safari_recovery.js`.

`session_recovery.js` remains responsible for API retry bridging, selected-team persistence, and trade presentation helpers, but it delegates restore work to `window.fsfflRestoreSession` and must not call the synchronous Sleeper connect endpoint itself.

This preserves restore-first/background-revalidate behavior and prevents duplicate provider acquisition after restart or recoverable UI errors.
