# Parallel waves

A wave starts when every task it depends on has a receipt. Inside a wave, tasks run together. Two tasks share a wave only if their write scopes are different paths.

Do not start a later wave by editing a file that an earlier task owns. Do not delete a duplicate scraper tree from any wave. Retirement lists are the output. Removal waits for a named go-ahead.

| Wave | Tasks | Wait for | What runs together |
| --- | --- | --- | --- |
| A | LCM-000, LCM-001, LCM-002, LCM-003, LCM-004, LCM-005, LCM-006, LCM-007, LCM-008, LCM-009, LCM-082 | nothing | Read-only inventories and the non-admission check. Eleven workers, eleven output files. |
| B | LCM-010, LCM-011, LCM-012, LCM-013, LCM-014, LCM-015, LCM-016, LCM-017 | the one inventory each names | Eight registers in eight files. |
| C | LCM-018 | LCM-010 through LCM-015 | One worker writes `instrument_v1.py`. Kind modules wait for this file so they import a real module. |
| D | LCM-020, LCM-021, LCM-022, LCM-023, LCM-024, LCM-025, LCM-026 | LCM-018 and that kind's register | Seven kind files. None of them edit `instrument_v1.py` or a package `__init__.py`. |
| E | LCM-030, LCM-031, LCM-032, LCM-033, LCM-034, LCM-035, LCM-036, LCM-037, LCM-038, LCM-039, LCM-040, LCM-041, LCM-042, LCM-043 | the kind module or register each names | Fourteen adapter and guard tasks, each a new file or a test. LCM-041, LCM-042, and LCM-043 may start as soon as LCM-016 is done; they do not wait for Wave D. |
| F | LCM-050 | Wave D and Wave E adapters LCM-030 through LCM-040 | One index module. |
| G | LCM-051, LCM-052, LCM-053 | LCM-050 and LCM-016 | Three boundary files in three trees. No bulk rewrite. |
| H | LCM-060 | LCM-017 and LCM-020 through LCM-026 | One display contract. |
| I | LCM-061, LCM-062, LCM-063, LCM-064, LCM-065, LCM-066, LCM-067 | LCM-060 and the matching kind module | Site views and the SwissKnife package. Site tasks do not edit SwissKnife. LCM-066 does not edit the site or the visual-functional board. |
| J | LCM-070, LCM-071, LCM-072, LCM-073 | the code wave each cites | Docs read landed source. They can run as soon as their own code dependency is in, so they do not wait for unrelated views. |
| K | LCM-074 | LCM-009 and LCM-073 | Historical banners on old reports. |
| L | LCM-075, LCM-080, LCM-081, LCM-083 | the docs and the guards they check | Drift, version agreement, closed routes, explicit place, and a final non-admission check. |

LCM-041, LCM-042, and LCM-043 are in Wave E's list and may also start at the end of Wave B, beside Wave C, because they only need LCM-016.

Suggested worker split once Wave A is done:

- Worker law: LCM-010, then LCM-020, then LCM-030 and LCM-035, then LCM-061.
- Worker municipal: LCM-011, then LCM-025, then LCM-031 and LCM-032, then LCM-067.
- Worker regulation: LCM-013, then LCM-021, then LCM-033, then LCM-063.
- Worker acts: LCM-014, then LCM-022, then LCM-034, then LCM-064.
- Worker caselaw: LCM-012, then LCM-023, then LCM-036, LCM-037, LCM-038, and LCM-039 together only if each stays in its own new file, then LCM-062.
- Worker courts: LCM-015, then LCM-024, then LCM-040, then LCM-065.
- Worker boundary: LCM-007 and LCM-016, then LCM-042 and LCM-043, then LCM-051, LCM-052, and LCM-053 after LCM-050.
- Worker UI contract and SwissKnife: LCM-008, LCM-017, LCM-060, LCM-066.
- Worker docs: starts each doc task when its code task lands. Does not draft the post-refactor manual during Wave A.
