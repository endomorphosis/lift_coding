# Meta Ray-Ban Display Web App Package

This directory is a deployable static export for the task-progress display simulator. It is intentionally self-contained so it can be copied to any static host and loaded by Meta Ray-Ban Display glasses before the native iPhone DAT display migration.

## Package Contents

- `index.html`: fixed 600x600 browser entrypoint.
- `styles.css`: dark display theme with `overflow: hidden`.
- `app.js`: D-pad and Enter focus handling plus local ORB event persistence.
- `manifest.webmanifest`: fullscreen Web App manifest with PNG icons.
- `readiness.json`: linter input and operator metadata for hosted glasses loading.
- `icons/*.png`: PNG app icons, including the 52x52 minimum display icon.

## Hosting Checklist

1. Deploy the files in this directory without a build step.
2. Host them at a publicly available HTTPS URL.
3. Confirm `https://<host>/<path>/index.html`, `manifest.webmanifest`, and `readiness.json` return HTTP 200 without authentication.
4. Generate a QR code for the final `index.html` URL.
5. Add the HTTPS URL in the Meta AI app under `App Connections > Web apps`.
6. Open the Web App from the glasses and verify Arrow/D-pad focus and Enter activation.

The package remains a simulator path only. Native iPhone DAT work should consume the same manifest and trace after this hosted Web App path is validated.
