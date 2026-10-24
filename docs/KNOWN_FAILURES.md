# Known test failures (v1 freeze)

Full-suite audit on `rewrite/v1-body`, 2026-10-25. 17 tests failed. 16 are fixed; 1 remains and is documented below.
Run with the declared dependencies installed and `ADA_DATA_ROOT` pointing at an existing directory
(a missing root fails with `BodyFault: ada-data not mounted`).

## Still failing

| Test | Root cause | Why not fixed |
|---|---|---|
| `tests/test_m22_brief_include.py::test_teach_in_flow_brief_include_confirm` | The "Don't put gym in my morning brief" teach-in-flow is not wired into the chat loop. `route_utterance` returns verb `brief_include`, but `_maybe_pack_fast_path` (`src/ada/harness/loop.py`) has no branch for it, and `ada.harness.brief_spine` is imported only by tests. The turn falls through to the model, which the test forbids. | The test also fails at its own introducing commit (`08b94bd`, 2026-08-27), so it was never green here: this is missing feature work, not drift. Wiring it is new life-organ work, out of scope for a freeze. |

## Fixed in this pass (root causes)

| Group | Tests | Root cause | Fix |
|---|---|---|---|
| Clock time bombs | `test_watches_m09` f1, f2, f11, f13 | Fixtures dated 2026-08-14; `watch_run` used the real clock, so once those items passed `max_age_hours=168` every wake logged `too_old` and fetched nothing. `test_f3_allowlist_deny` had been passing only because of the same skip. | Pin `now=` (parameter already existed). |
| Clock time bombs | `test_people_reflection::test_today_birthday_soon_and_people_remind` | Hardcoded birthday `1990-09-25` fell outside the 14-day "soon" window. | Derive the date from today (Pacific/Auckland). |
| Stale vs source | `test_m19a_life_capture` f2, f6, f10; `test_m19b_view_registry` nutrition rows | Gateway `life_meal_log` refuses writes without a `meal_spine` resolve (`spine_required`, 2026-09-11). | Pass a no-hold spine resolve, as `test_m19a_today` does. |
| Stale vs source | `test_m19a_logs_foundation::test_append_meal_row` | `meal_log` refuses lines with no macros (`empty_macros`, 2026-08-29); `append_meal`'s placeholder has none. | Give the line a macro. |
| Stale vs source | `test_m19a_food_reference::test_thin_custom_treated_as_miss_when_usda_present` | `search_foods_resolved` calls `fetch_usda_search_hits`; the test patched the old single-hit function. | Patch the multi-hit function. |
| Contract drift | `test_m16_first_package::test_f12_today_is_strip_shaped` | M22 added `open_gym` and `brief_include` to `build_today`. | Add both to the allowed keys. |
| Real regression | `test_m19b_view_registry::test_boot_path_js_stays_syntax_conservative` | `stream.js` used `?.`, banned in boot-path JS for older browsers. | Explicit null-safe check (`src/ada/hud/static/js/stream.js`). |
| Ambient secret | `test_m25_resolve_recover` (2 tests) | USDA detail refresh needs `USDA_FDC_API_KEY`; tests mock HTTP but did not set a key, so they only passed where a real key existed. | `monkeypatch.setenv` in both tests. |

One test was removed rather than fixed: `test_m19a_life_capture::test_f7_today_nutrition_from_rollup` duplicated
`test_m19a_today::test_today_nutrition_from_rollup` (Today headline from the SQL rollup).
