# Warm research workspace: local source slice

Base: `91fbafce024795b071c0f03015945b055669de6b`. This preserves the earlier unpushed desktop-column candidate. The latest user direction is a warm orange frontend with clear functional areas. The existing F2-T09 [authenticated workspace](../../F2/InternalEntry.md) remains the scope; this is not a new workflow or capability.

Only `src/sim2act/web/app.css` changes in the product. Warm white canvas, white results, a softer input area and deep brown navigation separate the existing content areas. Orange primary actions/current locations and separate page/sidebar focus colors replace the green brand treatments. Two small eyebrow labels increase to 11px. Original response bodies, request keys, confirmation controls and disclosure contents stay intact. Result numerals use neutral ink, not a semantic-success brand color.

Error, UNKNOWN, loading and success selectors/declarations remain byte-equivalent after CSS parsing; those colors are intentionally distinct from the brand. Human acceptance and publication information are unchanged. Disabled styling stays separate, forced-colors focus uses `Highlight`, and the original reduced-motion and responsive rules remain.

## Actual local verification

`palette.json`: six offline assertions, including eleven representative numerical text/focus contrast pairs, complete non-color geometry/visibility/content/motion comparison against the base except the explicit eyebrow typography, unchanged dedicated state rules, hidden-content protection, system focus colors and no new external asset URL. The primary white/orange pair is 5.1656:1 and the current narrow navigation pair is 4.6334:1. These pairs do not establish whole-page WCAG conformance or actual composited colors.

`assets.json`: all 26 HTML/JS assets are byte-identical to the base. No business runtime suite was repeated for a CSS-only product change. CSS parsing, test-script syntax and `git diff --check` passed. The first test-harness attempt treated the leading whitespace in a CSS custom property as part of its hex value; normalizing parser whitespace corrected the harness, without changing product colors.

Readonly independent reviewer `/root/confirmed_model_probe_review` gave a limited source ACK: no new P1/P2 found; primary/hover white text, independent disabled styling, forced-color focus and the dedicated state rules were consistent. Review did not run a browser or network and does not sign pixels.

## Explicit limits

No rendering, screenshot, native device/fps measurement, model, HTTP, authentication retry, push or CI ran. The warm visual composition and inherited desktop sticky-column candidate remain pixel-unverified. Old native screenshots belong to their old execution SHA and do not attest this palette. The previous Git push rejection remains preserved and unretried; local source work is independent of that refusal. No API/browser/Worker child was started, and the finite local Node check exited normally.
