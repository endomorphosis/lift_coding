# PR-082 work log

## Checklist
- [ ] Locate current `image` input handling in `api.py`.
- [ ] Create OCR provider interface + stub provider.
- [ ] Wire into command pipeline.
- [ ] Add tests for strict rejection and successful OCR path.
- [ ] Run `python -m pytest -q`.

## Notes
- Keep stub deterministic and fixture-friendly.
- Avoid heavy system dependencies by default.
