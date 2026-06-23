# VAI-022 Browser Web App HTTPS Glasses Loading

Date: 2026-06-23
Task: VAI-022
Track: ui

## Scope

VAI-022 defines the browser Web App packaging and HTTPS glasses loading path
for glasses-accessible UI surfaces. It depends on the VAI-008 remote terminal
contract and the VAI-016 browser simulator shell, and it does not replace the
future native iPhone DAT display handoff.

## Package

The deployable package is `dev/meta-rayban-display-simulator/webapp/`.

Required files:

| File | Purpose |
| --- | --- |
| `index.html` | 600x600 display entrypoint for browser preview and hosted Web App loading. |
| `styles.css` | Fixed viewport display styling with hidden overflow. |
| `app.js` | D-pad focus, Enter activation, and ORB event persistence. |
| `manifest.webmanifest` | Fullscreen Web App manifest and PNG icon declarations. |
| `readiness.json` | Deployment URL, widget metadata, focus order, hosting requirements, and linter input. |
| `icons/icon-52.png`, `icons/icon-192.png` | Glasses-ready PNG icons. |

The package is intentionally static: copy the directory to a trusted HTTPS
static host without a build step. Do not require authentication for
`index.html`, `manifest.webmanifest`, `readiness.json`, or the referenced
assets.

## HTTPS Loading Modes

| Mode | Host | Glasses-loadable | Contract |
| --- | --- | --- | --- |
| Local development | `localhost` or local desktop browser | No, unless promoted through public HTTPS | Validate layout, 600x600 viewport, focus order, readiness metadata, and simulator fixture parity. |
| Phone-hosted | iPhone/mobile session host plus hosted Web App URL | Yes | Register the public HTTPS `deployment_url` in Meta AI app `App Connections > Web apps`; phone owns pairing, audio, command routing, and mobile-card fallback. |
| Desktop-hosted | Desktop-controlled static HTTPS origin | Yes | Serve the same package from GitHub Pages, Netlify, Vercel, or another trusted HTTPS static origin; desktop may expose operator/offload state while VAI-008 keeps the glasses constrained to terminal display behavior. |

## Required Path

1. Run local browser preview against
   `dev/meta-rayban-display-simulator/webapp/index.html`.
2. Validate readiness metadata with the display Web App readiness linter when
   available.
3. Publish the exact directory contents to a public HTTPS static origin.
4. Update `readiness.json.deployment_url` to the final HTTPS URL used by the
   glasses.
5. Confirm `index.html`, `manifest.webmanifest`, `readiness.json`, CSS, JS, and
   icons return HTTP 200 without authentication.
6. Register the HTTPS URL through Meta AI app `App Connections > Web apps`.
7. Launch on glasses and verify D-pad focus order `pause -> dismiss` and Enter
   activation.

## Constraints

- Plain HTTP, private IP addresses, local LAN hostnames, and authenticated
  preview URLs are not acceptable as final glasses loading URLs.
- The Web App remains a fallback and validation surface for the VAI-008 remote
  terminal route; mobile-card fallback must remain available when glasses or
  Web App loading is unavailable.
- Native iPhone DAT validation should consume the same widget IDs, focus order,
  and action semantics after this hosted browser Web App path is proven.

## Validation

Backlog validation command:

```bash
rg -n "VAI-022|HTTPS glasses loading|browser Web App" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
