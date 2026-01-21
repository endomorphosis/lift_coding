# PR-106: Remove legacy glasses-audio config plugin

## Checklist
- [ ] iOS dev-client build still succeeds after `npx expo prebuild --platform ios --clean`
- [ ] Glasses Diagnostics screen still shows Expo module available
- [ ] No runtime imports depend on `modules/glasses-audio`

## Verification notes
- If any feature still requires the legacy module, we should make that explicit and re-introduce it deliberately rather than via a hidden Podfile injection.
