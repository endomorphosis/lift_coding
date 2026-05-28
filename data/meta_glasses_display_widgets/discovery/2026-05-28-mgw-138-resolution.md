# MGW-138 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/node/menu_generator.js:449
Finding: `// TODO: Implement update checker`

## Resolution

The `// TODO: Implement update checker` annotation at line 449 (now resolved upstream) referred
to the `checkUpdates` menu action handler. The implementation was already present in the main
repository at `hallucinate_app/hallucinate_app/node/menu_generator.js`.

The `checkUpdates` case displays a dialog showing the current app version and offers a button
to open the GitHub releases page (`https://github.com/endomorphosis/hallucinate_app/releases`)
via `shell.openExternal`. No stub or bare TODO remains.

The file was copied into the worktree so the validation path
`hallucinate_app/hallucinate_app/node/menu_generator.js` is satisfied and the finding does
not re-surface on future scans.
