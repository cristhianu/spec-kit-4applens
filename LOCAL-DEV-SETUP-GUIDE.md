# Local Development Setup Guide

## Overview

This guide explains how to set up another project to use the latest Specify CLI features, including the Bicep generator, validation, and learnings database.

## What `install-local-dev.ps1` Does

The `install-local-dev` scripts (PowerShell and Bash) automate the complete setup:

1. ✅ Install Specify CLI in editable mode: `pip install -e ".[bicep]"`
2. ✅ Copy GitHub Copilot prompt files to `.github/prompts/`:
   - `speckit.bicep.prompt.md` - Bicep template generator
   - `speckit.validate.prompt.md` - Bicep template validator
3. ✅ Copy learnings database to `.specify/learnings/`:
   - `bicep-learnings.md` - Shared knowledge base (27+ entries)
4. ✅ Copy validation script to `scripts/`:
   - `bicep_validate_architecture.py` - SFI compliance validator
   - `README-VALIDATION-SCRIPT.md` - Validation documentation
5. ✅ Copy wrapper scripts to `scripts/bash/` and `scripts/powershell/`:
   - Convenience wrappers for validation commands

**What it does NOT do:**

- ❌ Copy test fixtures
- ❌ Set up Python test utilities

## Complete Setup Instructions

### Step 1: Run install-local-dev Script

**PowerShell (Windows):**

```powershell
# From your test project directory
C:\git\spec-kit-4applens\scripts\powershell\install-local-dev.ps1
```

**Bash (Linux/macOS):**

```bash
# From your test project directory
/path/to/spec-kit-4applens/scripts/bash/install-local-dev.sh
```

This automatically creates:

```text
your-project/
├── .github/
│   └── prompts/
│       ├── speckit.bicep.prompt.md
│       └── speckit.validate.prompt.md
├── .specify/
│   └── learnings/
│       └── bicep-learnings.md
└── scripts/
    ├── bicep_validate_architecture.py
    ├── README-VALIDATION-SCRIPT.md
    ├── bash/
    │   ├── bicep-validate-wrapper.sh
    │   └── bicep-validate.sh
    └── powershell/
        ├── bicep-validate-wrapper.ps1
        └── bicep-validate.ps1
```

### Step 2: Verify Installation

**Check installed components:**

```powershell
# Verify CLI installed
specify --version

# Check prompt files
Test-Path ".github\prompts\speckit.bicep.prompt.md"
Test-Path ".github\prompts\speckit.validate.prompt.md"

# Check learnings database
Test-Path ".specify\learnings\bicep-learnings.md"

# Check validation script
Test-Path "scripts\bicep_validate_architecture.py"

# Check wrapper scripts
Test-Path "scripts\bash\bicep-validate-wrapper.sh"
Test-Path "scripts\powershell\bicep-validate-wrapper.ps1"
```

## Using the Features

### 1. Generate Bicep Templates

**Via GitHub Copilot:**
```
/speckit.bicep
```

**Via CLI:**
```bash
# Analyze project only
specify bicep --analyze-only

# Generate templates
specify bicep
```

### 2. Validate Bicep Templates

**Via GitHub Copilot:**
```
/speckit.validate
```

**Via CLI:**
```bash
# Validate specific project
specify bicep validate --project "my-api"

# With custom options
specify bicep validate --project "backend" --verbose
```

### 3. Validate Architecture Compliance

**Using validation script:**
```bash
# Basic validation
python scripts/bicep_validate_architecture.py bicep-templates/main.bicep

# Detailed output
python scripts/bicep_validate_architecture.py bicep-templates/main.bicep --verbose

# CI/CD integration
python scripts/bicep_validate_architecture.py bicep-templates/main.bicep --json > validation-results.json
```

## What You Get

### Files Created by install-local-dev

| File | Location | Purpose |
|------|----------|---------|
| `speckit.bicep.prompt.md` | `.github/prompts/` | GitHub Copilot command for Bicep generation |
| `speckit.validate.prompt.md` | `.github/prompts/` | GitHub Copilot command for validation |
| `bicep-learnings.md` | `.specify/learnings/` | Shared learnings database (27+ entries) |
| `bicep_validate_architecture.py` | `scripts/` | SFI compliance validation script |
| `README-VALIDATION-SCRIPT.md` | `scripts/` | Validation script documentation |
| `bicep-validate-wrapper.sh` | `scripts/bash/` | Bash wrapper for validation |
| `bicep-validate.sh` | `scripts/bash/` | Bash validation script |
| `bicep-validate-wrapper.ps1` | `scripts/powershell/` | PowerShell wrapper |
| `bicep-validate.ps1` | `scripts/powershell/` | PowerShell validation script |

## Troubleshooting

### Issue: "Learnings database not found"

**Symptom:** `/speckit.bicep` or `/speckit.validate` fails with missing learnings error

**Solution:** Verify `.specify/learnings/bicep-learnings.md` exists. Re-run install-local-dev script if needed.

### Issue: "Validation script not found"

**Symptom:** `python scripts/bicep_validate_architecture.py` fails

**Solution:** Re-run the install-local-dev script to ensure all files are copied. The script should automatically install validation scripts.

### Issue: "Module 'specify_cli' not found"

**Symptom:** CLI commands fail with import errors

**Solution:** Ensure you installed in editable mode: `pip install -e "C:\git\spec-kit-4applens[bicep]"`

### Issue: "Prompt files in wrong location"

**Symptom:** Prompt files created in subdirectory instead of project root

**Solution:** Updated scripts (v0.1.0+) fix this issue. They now capture project root at execution time and install files at `$projectRoot/.github/prompts/` and `$projectRoot/.specify/learnings/`.

## Advanced Configuration

### Customize Learnings Database

You can add custom organizational learnings:

```bash
# Edit learnings database
code .specify/learnings/bicep-learnings.md
```

**Format:**
```markdown
[2025-11-04T10:00:00Z] Category Context → Issue → Solution
```

**Example:**
```markdown
[2025-11-04T10:00:00Z] Security Azure Storage → Public access allowed → Set publicNetworkAccess: 'Disabled'
```

### CI/CD Integration

**Azure Pipelines:**
```yaml
- script: python scripts/bicep_validate_architecture.py main.bicep
  displayName: 'Validate Bicep Architecture'
  continueOnError: false
```

**GitHub Actions:**
```yaml
- name: Validate Bicep
  run: python scripts/bicep_validate_architecture.py main.bicep
```

## Updates and Maintenance

### Updating to Latest Version

1. **Update Specify CLI:**

   ```bash
   cd C:\git\spec-kit-4applens
   git pull
   ```

2. **Re-run install-local-dev** in your project:

   ```powershell
   C:\git\spec-kit-4applens\scripts\powershell\install-local-dev.ps1 -Force
   ```

   This will automatically update all prompt files, learnings database, validation scripts, and wrappers.

### Keeping Learnings Database Updated

The learnings database grows as you encounter and solve new issues. You can:

1. **Auto-capture from validation failures** (if using `/speckit.validate`)
2. **Manually add entries** from your team's experiences
3. **Sync from spec-kit** periodically:
   ```powershell
   Copy-Item "C:\git\spec-kit-4applens\.specify\learnings\bicep-learnings.md" -Destination ".specify\learnings\" -Force
   ```

## Summary

**Complete setup (fully automated):**

- Run `install-local-dev.ps1` → Get everything:
  - ✅ Specify CLI in editable mode
  - ✅ GitHub Copilot prompt files (`/speckit.bicep`, `/speckit.validate`)
  - ✅ Learnings database (27+ curated entries)
  - ✅ Architecture validation script (SFI compliance)
  - ✅ Wrapper scripts (bash and PowerShell)
  - ✅ Complete documentation

**Optional manual setup:**

- Test fixtures (only needed for Specify CLI development)
- Custom organizational configurations

The install-local-dev script now handles everything you need! 🚀
