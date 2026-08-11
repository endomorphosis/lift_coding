# SCA ↔ UI/UX IR mapping for SwissKnife UI contracts

**Status:** ENABLE-UIR seed (2026-08-06)  
**Program:** SwissKnife Symbolic Contract Assurance (`SCA-`)  
**Depends on:** SCA-ENABLE-DOCTOR, SCA-643  

## Purpose

Route SwissKnife **web apps**, **virtual UI**, and **ORB** control surfaces through
UI/UX IR (UIR) formal projections where supported, and emit **typed unsupported**
dispositions elsewhere. This is the SCA binding surface for formal-first UI repair
(not open-ended LLM edits of large UI trees).

## Surface classes

| Class | Primary paths | UIR projection | SCA contract role |
|-------|---------------|----------------|-------------------|
| Web apps | `swissknife/src/apps/**`, web UI services | Component/tree IR + event calculus for interactions | Declared app contracts vs actual render tree |
| Virtual UI | `src/handsfree/swissknife_virtual_ui.py` | Virtual desktop / control surface IR | ORB-facing capability contracts |
| ORB / MCP-IDL | SwissKnife MCP++/ORB bindings | IDL projection of callable surfaces | tools/list truthfulness + call schema |
| Unsupported | Legacy HTML archives, one-off scripts | **unsupported** disposition | Must not silent-pass |

## Round-trip policy

1. **Supported:** snapshot → UIR IR → FOL/event facts → obligation compile → doctor/RPR packet.
2. **Unsupported:** explicit `uir_unsupported` finding with path + reason; no LLM write authority.
3. **Doctor bridge:** UI findings enter `sca_doctor_bridge.map_finding` as
   `contract_mismatch` / `surface_missing` / abstention — never as free-form edits.

## Fixture / conformance root

- Runtime receipts: `data/agent_supervisor/swissknife_contract_assurance/uir/`
- Doctor bridge: `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_doctor_bridge.py`
- RPR gate: `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_rpr_admission.py`

## Acceptance (ENABLE-UIR)

- [x] Mapping covers web apps, virtual UI, and ORB bindings.
- [x] Unsupported paths are a first-class disposition (table above).
- [ ] At least one automated round-trip fixture under `data/agent_supervisor/swissknife_contract_assurance/uir/` (follow-on).

## Non-goals

- Bulk LLM rewrite of UI trees.
- Claiming kernel proof from UIR alone.
