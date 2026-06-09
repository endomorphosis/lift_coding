# MGW-321 Resolution

Date: 2026-06-09
Source finding: `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-321-codebase-scan-c8b8fb51a6b1.md`
Evidence: `data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md:22`
Kind: false_positive

## Finding

The automated codebase scan flagged line 22 of the VAI-198 resolution document as a
`swallowed_exception`.  The flagged text is:

> - Changed all three `except Exception` `:` clauses to `except Exception as exc:`

This line is **documentation** describing the fix that was applied during VAI-198, not
live Python code.  The scanner matched the `except Exception` text pattern inside a
markdown prose description.

## Verification

The actual Python source was checked and the fix is fully in place:

```
grep -n "except Exception" hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Result:
```
380:    except Exception as exc:  # pragma: no cover - exact upstream failures vary.
513:    except Exception as exc:
772:        except Exception as exc:
786:            except Exception as exc:
1027:        except Exception as exc:
1036:        except Exception as exc:
1045:        except Exception as exc:
```

Every `except Exception` in the file already binds the exception to `exc`.  The three
clauses inside `_serialize_ipfs_value()` (lines 1027, 1036, 1045) — the specific scope
of VAI-198 — all use `except Exception as exc:` with `exc_info=exc` in the corresponding
`_logger` call.  No bare `except Exception:` remains.

## Resolution

This finding is a **false positive**.  No code change was required.

The VAI-198 resolution document (`data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md`)
was updated to append a `## Scanner Notes (MGW-321)` section that explains why future
scanner runs should treat findings from that file as false positives.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exits with code 0.

```
test -f data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md
```

Exits with code 0.
