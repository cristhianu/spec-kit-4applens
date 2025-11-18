# Implementation Plan: Shared Learnings Database for Bicep Generation and Validation

**Branch**: `004-bicep-learnings-database` | **Date**: October 31, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-bicep-learnings-database/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a shared learnings database (`.specify/learnings/bicep-learnings.md`) that both `/speckit.bicep` and `/speckit.validate` commands reference to prevent repeated errors and continuously improve template generation quality. The system will automatically capture structural errors (missing properties, invalid values, quota issues) while ignoring transient failures (throttling, timeouts), use semantic similarity (>70% threshold) to prevent duplicates, and maintain sub-2-second loading performance up to 250 entries through category-based filtering. Initial implementation includes extracting existing guidelines from prompt files and updating architectural defaults (remove Azure Front Door, replace Network Security Perimeter with Private Endpoints, enforce VNet isolation per SFI best practices).

## Technical Context

**Language/Version**: Python 3.11+ (for Specify CLI components), Markdown (for learnings database format)
**Primary Dependencies**: 
- Existing: `specify-cli` package (Python), file I/O operations
- New: scikit-learn (TF-IDF vectorization + cosine similarity with 60% threshold - adjusted from 70% to compensate for keyword-based matching)
**Storage**: File-based (`.specify/learnings/bicep-learnings.md` - Markdown format with structured categories)
**Testing**: pytest (existing test infrastructure in `tests/` directory)
**Target Platform**: Cross-platform (Windows/Linux/macOS) - runs within VS Code/IDEs with AI agent support
**Project Type**: CLI extension + prompt modification (extends existing Specify CLI)
**Performance Goals**: 
- Database loading: <2 seconds for up to 250 entries
- Semantic similarity check: <500ms per comparison
- File append operations: <100ms
**Constraints**: 
- Must work with existing `/speckit.bicep` and `/speckit.validate` command infrastructure
- Backward compatibility with existing prompt files required during migration
- Human-readable format (Markdown) for manual editing
**Scale/Scope**: 
- Initial migration: ~50-100 existing guidelines from prompt files
- Growth rate: 5+ entries/week during active development
- Maximum optimized size: 250 entries before requiring filtering

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Simplicity and Clarity
**Status**: ✅ PASS
- Simple file-based storage (Markdown)
- Straightforward keyword matching for error classification
- Clear semantic similarity threshold (70%)

### II. Root Cause Solutions
**Status**: ✅ PASS
- Addresses root cause: repeated errors from missing knowledge base
- Not a workaround: creates systematic learning mechanism

### III. Explicit Failure Over Silent Defaults
**Status**: ✅ PASS
- Semantic similarity comparison explicitly passes/fails (>70% = duplicate)
- Error classification uses explicit keyword lists
- No silent fallbacks in loading or appending operations

### IV. Early and Fatal Error Handling
**Status**: ✅ PASS  
- File I/O errors (missing directory, write permissions) fail immediately
- Invalid learning entry format rejected at append time
- Loading timeout (>2s) raises explicit performance error

### V. Iterative Development Approach
**Status**: ✅ PASS
- Phase 1: Basic file creation + manual migration (working end-to-end)
- Phase 2: Add automatic error capture
- Phase 3: Add semantic similarity duplicate detection
- Phase 4: Add category filtering for performance optimization

### VI. Minimal and Focused Changes
**Status**: ✅ PASS
- Changes limited to: creating learnings database, updating prompt files, adding reference logic
- No refactoring of existing `/speckit.bicep` or `/speckit.validate` core logic
- Architectural defaults (Front Door, NSP) updated only in prompt files and learnings database

### VII. Engineering Excellence Through Simplicity  
**Status**: ✅ PASS
- Reuses existing pytest testing infrastructure
- Functional approach: load → filter → apply (no OOP overhead)
- Utility functions for: parsing entries, checking similarity, filtering by category

**GATE RESULT**: ✅ ALL CHECKS PASSED - Proceed to Phase 0

---

## Project Structure

### Documentation (this feature)

```text
specs/004-bicep-learnings-database/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── contracts/           # Phase 1 output (/speckit.plan command)
```

### Source Code (repository root)

```text
.specify/
└── learnings/
    └── bicep-learnings.md         # Shared learnings database (new)

.github/
└── prompts/
    └── speckit.bicep.prompt.md    # Modified to reference learnings

templates/
└── commands/
    └── speckit.validate.prompt.md # Modified to reference learnings

src/
└── specify_cli/
    ├── __init__.py                # Version bump required
    └── utils/
        └── learnings_loader.py    # New: load/parse/filter learnings (new)

tests/
├── fixtures/
│   └── sample-learnings.md        # Test data (new)
└── unit/
    └── test_learnings_loader.py   # New: unit tests for loader utility
```

**Structure Decision**: Single project extension. Adding new `.specify/learnings/` directory for database storage, new utility module `learnings_loader.py` in existing `specify_cli/utils/`, and modifying existing prompt files. No architectural changes to CLI structure.

## Complexity Tracking

*No violations - Constitution Check passed all gates.*

---

## Phase 0: Outline & Research

**Status**: NOT STARTED

### Research Tasks

Based on Technical Context unknowns, the following research must be completed before Phase 1 design:

#### Task 1: Semantic Similarity Library Selection

**Question**: Which semantic similarity library should be used for 70% duplicate detection: sentence-transformers, spaCy, or simpler cosine similarity?

**Context**:
- Must achieve 70% similarity threshold for duplicate detection
- Performance target: <500ms per comparison
- Scale: up to 250 entries in database
- Python 3.11+ compatibility required
- Cross-platform support (Windows/Linux/macOS)

**Research Criteria**:
1. **Accuracy**: Can reliably detect 70% semantic similarity for Bicep error descriptions
2. **Performance**: Comparison speed for 250 entries
3. **Dependencies**: Installation complexity, package size, offline capability
4. **Maintenance**: Library stability, community support, last update date

**Expected Output** (to be filled in `research.md`):
- **Decision**: [Chosen library name]
- **Rationale**: [Why chosen - address accuracy, performance, dependencies, maintenance]
- **Alternatives Considered**:
  - sentence-transformers: [Evaluation with pros/cons]
  - spaCy: [Evaluation with pros/cons]
  - Cosine similarity (simple): [Evaluation with pros/cons]

---

**Phase 0 Gate**: ✅ All research tasks must be resolved before proceeding to Phase 1.



