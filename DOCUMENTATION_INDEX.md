# Documentation Index

**Complete guide to all HandsFree Dev Companion documentation**

This index helps you find the right documentation for your needs, whether you're a new contributor, tester, or developer working on the project.

---

## 🚀 Start Here

**New to the project?** Start with one of these:

- **[Getting Started Guide](GETTING_STARTED.md)** - Complete setup for backend, mobile, and iPhone/Glasses testing
- **[README](README.md)** - Project overview and quick start
- **[Architecture](ARCHITECTURE.md)** - Understand system design and components

---

## 📋 By Role

### I'm a Developer

**Backend Development**:
- [Getting Started](GETTING_STARTED.md) - Setup guide
- [Architecture](ARCHITECTURE.md) - System design
- [Contributing](CONTRIBUTING.md) - Development workflow
- [Configuration](CONFIGURATION.md) - Environment variables
- [API Reference](spec/openapi.yaml) - OpenAPI specification

**Mobile Development**:
- [Mobile README](mobile/README.md) - App documentation
- [Build Instructions](mobile/BUILD.md) - Native module setup
- [Getting Started](GETTING_STARTED.md#mobile-app-setup) - Mobile setup
- [Mobile Client Integration](docs/mobile-client-integration.md) - API usage

### I'm a Tester

**iPhone & Meta Glasses Testing**:
- [Testing Quick Reference](docs/TESTING_QUICK_REFERENCE.md) - Quick reference card
- [MVP1 Runbook](docs/ios-rayban-mvp1-runbook.md) - Complete testing guide
- [Troubleshooting](docs/ios-rayban-troubleshooting.md) - Common issues
- [Demo Checklist](docs/mvp1-demo-checklist.md) - Pre-demo verification

**General Testing**:
- [Getting Started](GETTING_STARTED.md#verification--testing) - Testing procedures
- [Mobile README](mobile/README.md#testing) - Mobile testing guide

### I'm an Agent/Autonomous Developer

**Understanding the System**:
- [Getting Started](GETTING_STARTED.md) - Complete setup
- [Architecture](ARCHITECTURE.md) - System design and data flows
- [Configuration](CONFIGURATION.md) - All configuration options
- [API Reference](spec/openapi.yaml) - Complete API documentation
- [Contributing](CONTRIBUTING.md) - Development guidelines

**Implementation Details**:
- [Database Schema](ARCHITECTURE.md#database-schema) - Data models
- [Authentication](docs/AUTHENTICATION.md) - Auth flows
- [Agent Delegation](docs/agent-runner-setup.md) - Agent system

---

## 📚 By Topic

### Setup & Installation

| Document | Description | Audience |
|----------|-------------|----------|
| [Getting Started](GETTING_STARTED.md) | Complete setup guide | All |
| [Configuration](CONFIGURATION.md) | Environment variables | Developers |
| [Mobile README](mobile/README.md) | Mobile app setup | Mobile developers |
| [Build Instructions](mobile/BUILD.md) | Native module build | Mobile developers |

### Architecture & Design

| Document | Description | Audience |
|----------|-------------|----------|
| [Architecture](ARCHITECTURE.md) | System design | All |
| [README](README.md#system-architecture) | High-level overview | All |
| [Implementation Plan](implementation_plan/) | Design documents | Developers |
| [Command Grammar](spec/command_grammar.md) | Supported intents | Developers |

### API & Integration

| Document | Description | Audience |
|----------|-------------|----------|
| [OpenAPI Spec](spec/openapi.yaml) | Complete API reference | Developers |
| [Mobile Client Integration](docs/mobile-client-integration.md) | API usage patterns | Mobile developers |
| [Webhooks](docs/webhooks.md) | GitHub webhook integration | Developers |
| [Authentication](docs/AUTHENTICATION.md) | Auth modes and flows | Developers |

### iPhone & Meta Glasses

| Document | Description | Audience |
|----------|-------------|----------|
| [Testing Quick Reference](docs/TESTING_QUICK_REFERENCE.md) | Daily testing guide | Testers |
| [MVP1 Runbook](docs/ios-rayban-mvp1-runbook.md) | Complete runbook | Testers |
| [Meta Glasses Integration](docs/meta-ai-glasses.md) | Technical guide | Developers |
| [Audio Routing](docs/meta-ai-glasses-audio-routing.md) | Bluetooth details | Developers |
| [Troubleshooting](docs/ios-rayban-troubleshooting.md) | Common issues | Testers |

### Android & Emulator

| Document | Description | Audience |
|----------|-------------|----------|
| [Mobile README (Android)](mobile/README.md#run-on-simulator) | Android emulator setup and run commands | Mobile developers |
| [Meta Glasses Integration](docs/meta-ai-glasses.md) | Notes on Android + emulator Bluetooth/audio limitations | Developers |
| [Termux Phone Dispatcher](docs/termux-phone-dispatcher.md) | Run a phone-local GitHub dispatcher | Developers |

### Mobile Development

| Document | Description | Audience |
|----------|-------------|----------|
| [Mobile README](mobile/README.md) | Complete app guide | Mobile developers |
| [Build Instructions](mobile/BUILD.md) | Native builds | Mobile developers |
| [Glasses Module](mobile/glasses/README.md) | Native module docs | Mobile developers |
| [Push Notifications](docs/push-notifications.md) | Notification setup | Mobile developers |

### Android Workflows (In-Flight)

These Android workflow docs/tools are being developed in draft PRs and may not be on `main` yet:

| Document | Description | Audience |
|----------|-------------|----------|
| [PR #424](https://github.com/endomorphosis/lift_coding/pull/424) | Android emulator setup docs | Mobile developers |
| [PR #425](https://github.com/endomorphosis/lift_coding/pull/425) | Android emulator smoke script | Mobile developers |
| [PR #426](https://github.com/endomorphosis/lift_coding/pull/426) | Android physical device workflow + `adb reverse` helper | Mobile developers |
| [PR #428](https://github.com/endomorphosis/lift_coding/pull/428) | Dockerized Android emulator runner docs | Mobile developers |
| [PR #430](https://github.com/endomorphosis/lift_coding/pull/430) | Mobile Settings: backend URL presets (emulator vs device) | Mobile developers |
| [PR #432](https://github.com/endomorphosis/lift_coding/pull/432) | Phone dispatcher shared-secret auth | Mobile developers |
| [PR #433](https://github.com/endomorphosis/lift_coding/pull/433) | Android networking matrix | Mobile developers |

### Configuration & Deployment

| Document | Description | Audience |
|----------|-------------|----------|
| [Configuration](CONFIGURATION.md) | All config options | Developers |
| [Secret Management](docs/SECRET_STORAGE_AND_SESSIONS.md) | Vault integration | DevOps |
| [Agent Runner Setup](docs/agent-runner-setup.md) | Agent delegation | Developers |
| [Persistent Database](docs/persistent-database.md) | Database setup | DevOps |

### Development Process

| Document | Description | Audience |
|----------|-------------|----------|
| [Contributing](CONTRIBUTING.md) | Development workflow | Developers |
| [Security](SECURITY.md) | Security policies | All |
| [PR Changes](PR_CHANGES.md) | Recent changes | Developers |

---

## 🔍 By Use Case

### Use Case: "I want to start developing the backend"

1. [Getting Started](GETTING_STARTED.md#backend-setup) - Setup instructions
2. [Architecture](ARCHITECTURE.md#backend-server) - Understand components
3. [Configuration](CONFIGURATION.md#backend-configuration) - Configure environment
4. [Contributing](CONTRIBUTING.md#backend-development) - Development workflow
5. [OpenAPI Spec](spec/openapi.yaml) - API reference

### Use Case: "I want to develop the mobile app"

1. [Getting Started](GETTING_STARTED.md#mobile-app-setup) - Setup instructions
2. [Mobile README](mobile/README.md) - App documentation
3. [Build Instructions](mobile/BUILD.md) - Native module setup
4. [Mobile Client Integration](docs/mobile-client-integration.md) - API patterns
5. [Contributing](CONTRIBUTING.md#mobile-development) - Mobile workflow

### Use Case: "I want to test with iPhone and Meta Glasses"

1. [Testing Quick Reference](docs/TESTING_QUICK_REFERENCE.md) - Quick guide
2. [Getting Started](GETTING_STARTED.md#iphone--meta-glasses-testing) - Setup
3. [MVP1 Runbook](docs/ios-rayban-mvp1-runbook.md) - Complete guide
4. [Troubleshooting](docs/ios-rayban-troubleshooting.md) - Fix issues
5. [Demo Checklist](docs/mvp1-demo-checklist.md) - Preparation

### Use Case: "I want to test on Android (emulator or device)"

1. [Mobile README](mobile/README.md#run-on-simulator) - Emulator setup and run
2. [Mobile README](mobile/README.md#run-on-physical-device) - Install on a physical device
3. [Meta Glasses Integration](docs/meta-ai-glasses.md) - Bluetooth/audio routing notes

### Use Case: "I want to dispatch GitHub tasks from my phone"

1. [Termux Phone Dispatcher](docs/termux-phone-dispatcher.md) - Run the phone-local dispatcher
2. [Mobile README](mobile/README.md) - Configure the app to call the dispatcher

### Use Case: "I want to understand the system architecture"

1. [README](README.md#system-architecture) - High-level overview
2. [Architecture](ARCHITECTURE.md) - Detailed design
3. [Getting Started](GETTING_STARTED.md#overview) - Component overview
4. [Implementation Plan](implementation_plan/) - Design decisions
5. [Command Grammar](spec/command_grammar.md) - Intent system

### Use Case: "I want to configure the system for production"

1. [Configuration](CONFIGURATION.md#production-configuration) - Production settings
2. [Secret Management](docs/SECRET_STORAGE_AND_SESSIONS.md) - Secure secrets
3. [Authentication](docs/AUTHENTICATION.md) - Production auth
4. [Architecture](ARCHITECTURE.md#deployment-architecture) - Deployment options

### Use Case: "I want to add agent delegation"

1. [Agent Runner Setup](docs/agent-runner-setup.md) - Complete guide
2. [Configuration](CONFIGURATION.md#agent-delegation) - Configuration
3. [Architecture](ARCHITECTURE.md#data-flow) - Agent delegation flow
4. [Minimal Agent Runner](docs/MINIMAL_AGENT_RUNNER.md) - Quick setup

---

## 📖 Documentation by Directory

### Root Documentation

```
├── README.md                          # Project overview
├── GETTING_STARTED.md                 # Complete setup guide
├── ARCHITECTURE.md                    # System architecture
├── CONFIGURATION.md                   # Configuration guide
├── CONTRIBUTING.md                    # Development workflow
├── SECURITY.md                        # Security policies
├── LICENSE                            # License
└── CHANGELOG.md                       # Version history (future)
```

### docs/ Directory

```
docs/
├── TESTING_QUICK_REFERENCE.md         # Testing quick guide
├── ios-rayban-mvp1-runbook.md        # Complete iOS/Glasses runbook
├── ios-rayban-troubleshooting.md     # Troubleshooting guide
├── meta-ai-glasses.md                # Glasses integration
├── meta-ai-glasses-audio-routing.md  # Bluetooth audio technical
├── mobile-client-integration.md      # API usage patterns
├── AUTHENTICATION.md                  # Auth modes
├── agent-runner-setup.md             # Agent delegation
├── SECRET_STORAGE_AND_SESSIONS.md    # Secret management
├── push-notifications.md             # Push notification setup
├── termux-phone-dispatcher.md        # Phone-local GitHub dispatcher
├── webhooks.md                        # Webhook integration
├── mvp1-demo-checklist.md            # Demo preparation
└── ... (more specialized docs)
```

### mobile/ Directory

```
mobile/
├── README.md                          # Mobile app guide
├── BUILD.md                           # Native build instructions
├── IMPLEMENTATION_SUMMARY.md          # Implementation details
├── PUSH_NOTIFICATIONS_TESTING.md     # Push notification testing
└── glasses/
    └── README.md                      # Native module docs
```

### spec/ Directory

```
spec/
├── openapi.yaml                       # Complete API specification
└── command_grammar.md                 # Intent patterns
```

### implementation_plan/ Directory

```
implementation_plan/
├── PR-*.md                            # PR implementation plans
└── ... (design documents)
```

---

## 🔗 External Resources

### GitHub

- **Repository**: [endomorphosis/lift_coding](https://github.com/endomorphosis/lift_coding)
- **Issues**: Report bugs or request features
- **Discussions**: Ask questions or share ideas
- **Pull Requests**: Contribute code

### APIs & Services

- **OpenAI API**: [platform.openai.com](https://platform.openai.com) - TTS/STT
- **GitHub API**: [docs.github.com/rest](https://docs.github.com/rest) - GitHub integration
- **Expo**: [docs.expo.dev](https://docs.expo.dev) - Mobile framework
- **React Native**: [reactnative.dev](https://reactnative.dev) - Mobile UI

---

## 📝 Documentation Standards

### When to Update Documentation

Update documentation when:

- Adding new features
- Changing APIs or configuration
- Fixing bugs that affect usage
- Improving setup procedures
- Adding new dependencies

### Where to Document

| Change Type | Update |
|-------------|--------|
| New feature | README, GETTING_STARTED, relevant guide |
| API change | OpenAPI spec, mobile/README |
| Configuration | CONFIGURATION.md |
| Architecture | ARCHITECTURE.md |
| Setup procedure | GETTING_STARTED.md |
| Mobile feature | mobile/README.md |
| Testing procedure | TESTING_QUICK_REFERENCE.md |

### Documentation Style

- **Clear headings** - Use descriptive section titles
- **Code examples** - Include working examples
- **Step-by-step** - Number steps for procedures
- **Verify commands** - Test all commands work
- **Link related docs** - Cross-reference other documentation
- **Keep updated** - Update when code changes

---

## 🆘 Can't Find What You Need?

1. **Search the docs**: Use GitHub search or `grep`
2. **Check existing issues**: Someone may have asked already
3. **Ask in Discussions**: Start a new discussion
4. **Open an issue**: Request documentation improvement

### Improving This Documentation

Found a typo? Missing information? See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit improvements.

---

## 📊 Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| README.md | ✅ Complete | 2026-01-20 |
| GETTING_STARTED.md | ✅ Complete | 2026-01-20 |
| ARCHITECTURE.md | ✅ Complete | 2026-01-20 |
| CONFIGURATION.md | ✅ Complete | 2026-01-20 |
| CONTRIBUTING.md | ✅ Complete | 2026-01-20 |
| mobile/README.md | ✅ Complete | 2026-01-20 |
| TESTING_QUICK_REFERENCE.md | ✅ Complete | 2026-01-20 |
| OpenAPI Spec | ✅ Up to date | (check spec) |

---

**Documentation Index Version**: 1.0  
**Last Updated**: 2026-01-20

**Feedback**: Help improve this documentation by opening an issue or PR!
