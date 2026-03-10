# Documentation Alignment Plan

**Date:** March 9, 2026  
**Scope:** Align HandsFree documentation with actual codebase features  
**Total Gaps:** 47 (18 High, 16 Medium, 13 Low)

---

## Executive Summary

The codebase has **47 documentation gaps**. The most critical issues are:

1. **Database schema** - 20 tables exist but only 8 documented; no ERD
2. **OpenAPI spec** - ~40 endpoints implemented but 20+ missing from spec
3. **Agent system** - Powerful feature with minimal documentation
4. **Mobile app** - Only 6 of 11 screens documented
5. **Configuration** - 30+ environment variables undocumented

These gaps create friction for developers onboarding to the project and risk feature misuse.

---

## High-Severity Gaps (18 items) - PRIORITY ORDER

### Tier 1: Foundation (This sprint)

These gateway docs block understanding of everything else.

#### 1️⃣ **Database Schema Documentation**
- **What's missing:** Complete ERD + all 20 tables + relationships + data lifecycle
- **Current state:** Only 8 tables shown in ARCHITECTURE.md
- **Impact:** Developers can't understand data model or write correct queries
- **Action:** Create detailed schema docs with ERD diagram
- **Effort:** 2-3 hours
- **Files to update:** ARCHITECTURE.md, new schema reference doc

#### 2️⃣ **OpenAPI Specification Completeness** 
- **What's missing:** 20+ endpoints not in spec; card types undefined; error codes missing
- **Current state:** Spec exists but incomplete
- **Impact:** API users don't know what endpoints exist or how to use them
- **Action:** Add missing endpoints, request/response examples, auth schemes
- **Effort:** 3-4 hours
- **Files to update:** spec/openapi.yaml

#### 3️⃣ **Authentication Integration**
- **What's missing:** Protected endpoints not listed; AUTHENTICATION.md not linked; integration guide incomplete
- **Current state:** Detailed auth guide exists but buried
- **Impact:** Developers misunderstand which endpoints need what auth
- **Action:** Create endpoint→auth mapping table; link from main docs
- **Effort:** 1.5-2 hours
- **Files to update:** README.md, GETTING_STARTED.md, AUTHENTICATION.md, spec/openapi.yaml

#### 4️⃣ **Configuration Reference**
- **What's missing:** 30+ environment variables not documented (metrics, timeouts, feature flags, rates)
- **Current state:** Basic config in CONFIGURATION.md but incomplete
- **Impact:** Users can't tune system behavior; feature flags invisible
- **Action:** Create comprehensive config reference with advanced section
- **Effort:** 2 hours
- **Files to update:** CONFIGURATION.md, new config reference doc

---

### Tier 2: Core Features (Next sprint)

These document major features that users frequently need.

#### 5️⃣ **Agent Delegation Workflow**
- **What's missing:** End-to-end flow; provider selection logic; state machine; result retrieval
- **Current state:** Mentioned briefly in README
- **Impact:** Users don't understand how to use agent delegation effectively
- **Action:** Create workflow guide with diagrams + state machine
- **Effort:** 2-3 hours
- **Files to update:** New agent-delegation-workflow.md, ARCHITECTURE.md

#### 6️⃣ **Mobile App Screens**
- **What's missing:** Only 6 of 11 screens documented; experimental screens hidden
- **Current state:** Summary in mobile/README.md
- **Impact:** Mobile developers don't see full UI/UX patterns
- **Action:** Create comprehensive screen reference with per-screen breakdown
- **Effort:** 2 hours
- **Files to update:** mobile/README.md, new SCREENS_REFERENCE.md

#### 7️⃣ **Webhook Processing & Deduplication**
- **What's missing:** Event dedup algorithm; retry policy; state machine; notification throttling
- **Current state:** No documentation exists
- **Impact:** Developers don't understand reliability guarantees
- **Action:** Create webhook processing guide with diagrams
- **Effort:** 2 hours
- **Files to update:** New webhook-processing.md, ARCHITECTURE.md

#### 8️⃣ **Profiles System**
- **What's missing:** What each profile does; how to use; how to customize; voice commands
- **Current state:** Mentioned in README but not explained
- **Impact:** Users don't understand profile purpose or utilization
- **Action:** Create profiles guide with use-case examples
- **Effort:** 1.5 hours
- **Files to update:** New profiles-guide.md, README.md

#### 9️⃣ **Confirmation Flow**
- **What's missing:** Token lifecycle; timeout behavior; user experience; error handling
- **Current state:** No clear explanation
- **Impact:** Users confused about confirmation prompts and timeouts
- **Action:** Create confirmation flow guide with diagram
- **Effort:** 1 hour
- **Files to update:** ARCHITECTURE.md, mobile/README.md

---

### Tier 3: Provider Systems & Advanced Features (Later sprints)

These document plugin systems and advanced configuration.

#### 🔟 **TTS/STT Provider System**
- **What's missing:** Which providers available; how to switch; fallback behavior
- **Current state:** Mentioned but not documented
- **Effort:** 1.5 hours
- **Files to update:** CONFIGURATION.md, new provider-systems.md

#### 1️⃣1️⃣ **Transport Layer**
- **What's missing:** libp2p_bluetooth provider; how to use; connection model
- **Current state:** Experimental, stub provider used by default
- **Effort:** 1.5 hours
- **Files to update:** New transport-layer.md, ARCHITECTURE.md

#### 1️⃣2️⃣ **MCP Integration**
- **What's missing:** What MCP is used for; integration points; how to extend
- **Current state:** Mentioned in CODEBASE_INVENTORY but not in user docs
- **Effort:** 2 hours
- **Files to update:** New mcp-integration.md, ARCHITECTURE.md

#### 1️⃣3️⃣ **Secrets Management**
- **What's missing:** Comparison of Vault vs AWS vs GCP providers; rotation; setup per provider
- **Current state:** Partial documentation in VAULT_SECRET_MANAGER.md
- **Effort:** 1.5 hours
- **Files to update:** CONFIGURATION.md, new secrets-guide.md

#### 1️⃣4️⃣ **Privacy Modes**
- **What's missing:** Strict/Balanced/Debug modes; use-cases; per-handler enforcement
- **Current state:** Implemented but not in main docs
- **Effort:** 1 hour
- **Files to update:** README.md, new privacy-modes.md

#### 1️⃣5️⃣ **Push Notification Providers**
- **What's missing:** APNS vs FCM vs Expo; provider setup; testing
- **Current state:** push-notifications.md exists but incomplete
- **Effort:** 1 hour
- **Files to update:** push-notifications.md, CONFIGURATION.md

#### 1️⃣6️⃣ **GitHub Integration Features**
- **What's missing:** What operations are supported; limitations; error codes
- **Current state:** Scattered across multiple docs
- **Effort:** 1.5 hours
- **Files to update:** New github-integration.md, ARCHITECTURE.md

#### 1️⃣7️⃣ **Experimental Features Markup**
- **What's missing:** Which features are experimental vs stable; stability note
- **Current state:** Not marked in docs
- **Effort:** 0.5 hours
- **Files to update:** README.md, ARCHITECTURE.md, multiple feature docs

#### 1️⃣8️⃣ **API Response Card Types**
- **What's missing:** Card type definitions; per-card handler; rendering rules
- **Current state:** No documentation
- **Effort:** 1 hour
- **Files to update:** spec/openapi.yaml, new card-types.md

---

## Medium-Severity Gaps (16 items)

<details>
<summary>Click to expand medium-severity gaps</summary>

1. Intent recognition grammar not fully documented
2. Policy evaluation system not explained
3. Discord integration mentioned but not documented
4. Image analysis AI features not documented
5. IPFS integration overview missing
6. GitHub OAuth flow not fully explained
7. Rate limiting not documented
8. Error codes reference missing
9. Notification filtering rules not explained
10. Mobile testing procedures not documented
11. Command response filtering not explained
12. Database maintenance not documented
13. S3 integration not documented
14. Monitoring/observability not fully documented
15. Development workflow not fully explained
16. Mobile native module development not fully documented

</details>

---

## Low-Severity Gaps (13 items)

<details>
<summary>Click to expand low-severity gaps</summary>

1. Examples for voice commands not comprehensive
2. Troubleshooting guides missing for some features
3. Performance tuning guide missing
4. Load testing procedures not documented
5. Security hardening guide missing
6. Deployment options not fully documented
7. Development best practices not documented
8. Testing strategy framework not documented
9. Plugin development guide missing
10. Custom provider implementation guide missing
11. Scaling considerations incomplete
12. Multi-tenant setup not documented
13. Data retention policy not documented

</details>

---

## Estimated Timeline

| Tier | Items | Effort | Timeline |
|------|-------|--------|----------|
| **Tier 1** | 4 | ~8-9 hours | **1 sprint** |
| **Tier 2** | 5 | ~9-10 hours | **1 sprint** |
| **Tier 3** | 9 | ~13 hours | **2-3 sprints** |
| **Medium** | 16 | ~12-15 hours | **2 sprints** |
| **Low** | 13 | ~8-10 hours | **1-2 sprints** |
| **TOTAL** | 47 | ~50-60 hours | **~6-8 sprints** |

---

## Recommended PR Structure

### Sprint 1: Foundation (Tier 1 - 4 PRs)
Each PR addresses one gateway gap:

1. `docs: Add complete database schema with ERD`
2. `docs: Complete OpenAPI specification`
3. `docs: Link authentication and create endpoints reference`
4. `docs: Add configuration reference with advanced options`

### Sprint 2: Core Features (Tier 2 - 5 PRs)
Each PR documents one major feature:

5. `docs: Add agent delegation workflow guide`
6. `docs: Add mobile app screens reference`
7. `docs: Add webhook processing and deduplication guide`
8. `docs: Add profiles guide`
9. `docs: Add confirmation flow documentation`

### Sprint 3+: Provider Systems (Tier 3 - 9 PRs)
Each PR documents one provider system or advanced feature

---

## How to Proceed

### Option A: Sequential Top-Down (Recommended)
1. Create Tier 1 PRs (this sprint)
2. Merge Tier 1 PRs first
3. Create Tier 2 PRs (next sprint)
4. Continue with Tier 3 + Medium

**Benefit:** Unblocks developers immediately; foundation is solid

### Option B: Parallel by Category
1. Group by category (API, Mobile, Config, Providers)
2. Create all 4 Tier 1 PRs simultaneously
3. Create Tier 2 PRs for each category in parallel

**Benefit:** Faster overall completion; higher coordination needs

---

## Success Criteria

A PR is complete when:
- [ ] Feature is fully documented with examples
- [ ] Linked from relevant docs (README, ARCHITECTURE, etc.)
- [ ] Multiple ways to find: search should work
- [ ] Examples show realistic usage
- [ ] Related configuration documented
- [ ] Error cases documented
- [ ] It passes review as complete/actionable

---

## Quick Reference: Files to Create/Update

### New Documentation Files (Tier 1)
- [ ] `docs/database-schema.md` - Schema ERD + table reference
- [ ] `docs/configuration-reference.md` - All env vars with defaults
- [ ] Update `ARCHITECTURE.md` - Protected endpoints table

### New Documentation Files (Tier 2)
- [ ] `docs/agent-delegation-workflow.md` - Complete workflow guide
- [ ] `mobile/SCREENS_REFERENCE.md` - All 11 screens
- [ ] `docs/webhook-processing.md` - Event processing + dedup
- [ ] `docs/profiles-guide.md` - Profile reference
- [ ] `docs/confirmation-flow.md` - Confirmation UX + token lifecycle

### Files to Update (All Tiers)
- [ ] `README.md` - Add links to new feature docs
- [ ] `ARCHITECTURE.md` - Expand sections, add diagrams
- [ ] `GETTING_STARTED.md` - Add agent/webhook/profile setup
- [ ] `CONFIGURATION.md` - Link to detailed config
- [ ] `spec/openapi.yaml` - Complete spec
- [ ] `mobile/README.md` - Link to screens reference
- [ ] `DOCUMENTATION_INDEX.md` - Update with all new docs

---

## Notes

1. **CODEBASE_INVENTORY.md** exists as reference for what's actually in code
2. **DOCUMENTATION_GAP_ANALYSIS.md** has detailed breakdown of each gap
3. This plan focuses on **user-facing** gaps (blocks understanding)
4. Internal code documentation (docstrings) separate concern
5. Experimental features should be labeled `⚠️ EXPERIMENTAL` in docs

---

Generated by comprehensive codebase + documentation review on March 9, 2026.

See **DOCUMENTATION_GAP_ANALYSIS.md** for detailed gap descriptions and code locations.
