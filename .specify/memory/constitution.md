<!--
SYNC IMPACT REPORT
==================
Version Change: 1.0.0 → 1.1.0
Change Type: MINOR (new section added with materially expanded guidance)

Modified Principles:
- EXISTING: I-VI remain unchanged

Added Sections:
- Development Philosophy (NEW)
  - Core Philosophy: Simplicity, root cause fixes, fail-fast approach
  - Error Handling: Early, clear, fatal errors; avoid try/except wrapping
  - Development Approach: Incremental end-to-end implementation
  - Best Practices: Code reuse, decomposition, testability, minimal abstraction
  - Collaboration: AI as thoughtful collaborator, not blind executor

Templates Requiring Updates:
✅ plan-template.md - Development Philosophy aligns with existing simplicity gates
✅ spec-template.md - No changes needed (focused on requirements)
✅ tasks-template.md - Incremental approach aligns with phased task breakdown

Follow-up TODOs:
- None - Development Philosophy complements existing principles
-->

# Spec Kit Constitution

## Core Principles

### I. Specification-First Development

All development MUST begin with executable specifications that define requirements, user stories, and acceptance criteria before any implementation or technical planning occurs.

**Non-Negotiable Rules:**

- No implementation plans without approved feature specifications
- No code generation without complete implementation plans
- Specifications define WHAT and WHY, never HOW
- All ambiguities MUST be marked with `[NEEDS CLARIFICATION]` tags
- User stories MUST be prioritized (P1, P2, P3...) and independently testable

**Rationale:** Specifications serve as the single source of truth, eliminating the gap between intent and implementation. By starting with clear requirements, we ensure that all subsequent work—planning, tasking, implementation—remains aligned with user needs and business goals. The executable nature of specifications means they directly generate working systems rather than merely guiding development.

### II. Template-Driven Quality

All specifications, plans, and tasks MUST use standardized templates that enforce structure, completeness, and consistency.

**Non-Negotiable Rules:**

- Feature specifications use `spec-template.md` format
- Implementation plans use `plan-template.md` format  
- Task breakdowns use `tasks-template.md` format
- Templates act as "unit tests for English" - enforcing quality gates
- Constitutional compliance MUST be verified at Phase -1 (pre-implementation gates)

**Rationale:** Templates constrain AI behavior toward higher-quality outputs by preventing premature implementation details, forcing explicit uncertainty markers, providing structured self-review checklists, and ensuring proper information hierarchy. This transforms AI from creative writer to disciplined specification engineer.

### III. Test-First Imperative (NON-NEGOTIABLE)

All implementation MUST follow strict Test-Driven Development (TDD). No implementation code shall be written before tests are written, validated, approved, and confirmed to FAIL.

**Non-Negotiable Rules:**

- Tests MUST be written before implementation code
- Tests MUST be reviewed and approved by maintainers
- Tests MUST fail initially (Red phase) before implementation begins
- Red-Green-Refactor cycle strictly enforced
- Contract tests are mandatory before any implementation
- Integration tests MUST use realistic environments (real databases, not mocks)

**Rationale:** Test-first development ensures code is designed for testability from the start, provides clear acceptance criteria, catches design flaws early, and creates living documentation. This principle completely inverts traditional AI code generation - instead of generating code and hoping it works, we first generate comprehensive tests that define behavior, get them approved, and only then generate implementation. Critical failures (like missing learnings databases) trigger explicit HALT behavior per this principle.

### IV. Modular Architecture

Features MUST be developed as standalone, reusable components with clear boundaries, minimal dependencies, and well-defined interfaces.

**Non-Negotiable Rules:**

- Maximum 3 projects for initial implementation (additional projects require justification)
- No future-proofing or speculative features
- Use framework features directly rather than wrapping them unnecessarily
- Single model representation (no redundant abstractions)
- Libraries MUST be self-contained and independently testable
- CLI interfaces required for all libraries (text in/out protocol)

**Rationale:** Modular design ensures maintainability, reusability, and testability. By limiting project complexity and avoiding premature abstractions, we keep systems understandable and evolvable. CLI interfaces provide observability and enable automation.

### V. Multi-Agent Support

The toolkit MUST support multiple AI coding assistants while maintaining consistent project structure and development practices.

**Non-Negotiable Rules:**

- Agent-specific command files follow agent conventions (Markdown, TOML, etc.)
- All agents access the same underlying specifications and templates
- Agent integrations MUST be documented in AGENTS.md
- New agent additions require updates to both install scripts (bash and PowerShell)
- Agent-specific files MUST NOT contain agent-specific implementation details (use placeholders like `__AGENT__`)

**Rationale:** Different teams use different AI tools. By supporting multiple agents while maintaining a unified methodology, we allow teams to choose their preferred tools without fragmenting the development process. Consistency across agents ensures specifications remain the lingua franca regardless of the AI assistant used.

### VI. Documentation as Code

All documentation MUST be versioned, structured, and maintained alongside code with the same rigor as production code.

**Non-Negotiable Rules:**

- Documentation lives in the repository (specs/, docs/, .specify/memory/)
- Feature specifications tracked in Git branches (e.g., 001-feature-name)
- Constitutional changes require version increments following semantic versioning
- README.md, AGENTS.md, and technical documentation kept synchronized
- Learnings databases capture and share knowledge across features (.specify/learnings/)

**Rationale:** Documentation that diverges from code becomes misleading and eventually ignored. By treating documentation as code—versioning it, reviewing it, testing it—we ensure it remains accurate, useful, and discoverable. The learnings database creates organizational memory that improves quality over time.

## Development Philosophy

### Core Philosophy

Prioritize code that is simple, easy-to-understand, debuggable, and readable above clever or overly complex solutions.

**Guiding Principles:**

- **Simplicity First**: Simple code is maintainable code. Avoid unnecessary complexity.
- **Fix Root Causes**: Address the underlying problem rather than applying superficial fixes. Band-aid solutions accumulate technical debt.
- **Fail Fast**: Avoid fallbacks and defaults when input assumptions aren't met. Explicit failures are better than silent misbehavior that propagates errors downstream.

**Rationale:** Simple, straightforward code reduces cognitive load, makes debugging easier, and allows team members to understand and modify systems quickly. Root cause fixes prevent recurring issues. Failing fast exposes problems immediately rather than allowing them to cascade.

### Error Handling

Errors MUST be raised early, clearly, and fatally to prevent silent failures and cascading issues.

**Non-Negotiable Rules:**

- Raise errors as soon as invalid conditions are detected
- Error messages MUST be clear and actionable
- Prefer fatal errors over silent degradation
- Avoid wrapping code in try/except blocks unless recovery is truly needed
- Let tracebacks propagate naturally for easier debugging

**Rationale:** Early, clear errors make debugging straightforward. Wrapping everything in try/except hides the actual failure point and makes root cause analysis difficult. Tracebacks provide valuable context for understanding what went wrong.

### Development Approach

Build incrementally: get a simple version working end-to-end first, then gradually layer in complexity.

**Non-Negotiable Rules:**

- Do not attempt to write a full, final version immediately
- Establish end-to-end functionality with the simplest possible implementation first
- Add complexity incrementally in focused stages
- Keep changes minimal and focused on the current task
- Resist the urge to over-engineer or add "nice to have" features preemptively

**Rationale:** Incremental development reduces risk, provides early validation, and makes debugging easier. Each stage can be tested independently. Trying to build everything at once often leads to wasted effort on features that turn out to be unnecessary or incorrectly designed.

### Best Practices

Follow software engineering best practices to maintain code quality and sustainability.

**Mandatory Practices:**

- **Code Reuse**: Identify and extract reusable functionality into utility functions
- **Function Decomposition**: Break long or complex functions into smaller, focused units
- **Testability**: Write code that is easy to test; prefer functional style over stateful approaches
- **Avoid Over-Abstraction**: Use object-oriented patterns only when they provide clear benefits; prefer simpler approaches otherwise
- **Documentation Currency**: Keep documentation up-to-date as code evolves; stale documentation is worse than no documentation
- **Library Selection**: When choosing 3rd-party libraries, prefer those with large, active communities for better support and longevity

**Rationale:** These practices compound over time. Reusable code reduces duplication. Small functions are easier to understand and test. Testable code catches regressions early. Minimal abstraction reduces mental overhead. Current documentation serves as reliable reference. Well-supported libraries reduce maintenance burden.

### Collaboration

AI agents MUST act as thoughtful collaborators, not blind executors.

**Non-Negotiable Rules:**

- If the user asks a question, answer it directly and pause other work until consensus is reached
- Proactively suggest improvements or alternatives when better approaches are identified
- Question decisions that seem incorrect or suboptimal rather than implementing them blindly
- Engage in discussion when requirements don't make sense or conflict with principles
- Help make good decisions through reasoned argument and evidence

**Rationale:** Effective collaboration requires critical thinking and honest communication. Blind obedience leads to poor outcomes when requirements are unclear or misguided. AI agents serve users best by applying judgment and offering expertise, not by silently implementing questionable decisions.

## Development Standards

### Workflow Phases

1. **Constitution Phase** (`/speckit.constitution`): Establish or update project governing principles
2. **Specification Phase** (`/speckit.specify`): Define requirements and user stories
3. **Clarification Phase** (`/speckit.clarify`): Resolve ambiguities through structured questioning
4. **Planning Phase** (`/speckit.plan`): Create technical implementation plans
5. **Tasking Phase** (`/speckit.tasks`): Break down plans into actionable tasks
6. **Analysis Phase** (`/speckit.analyze`): Validate cross-artifact consistency
7. **Implementation Phase** (`/speckit.implement`): Execute tasks following TDD

### Branching Strategy

- Feature branches named `###-feature-name` (e.g., `001-create-taskify`)
- Main branch contains stable, tested code
- Pull requests require:
  - Complete feature specification
  - Approved implementation plan
  - Passing tests
  - Constitutional compliance verification

### Version Management

Constitution versions follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Backward incompatible governance/principle removals or redefinitions
- **MINOR**: New principles/sections added or materially expanded guidance
- **PATCH**: Clarifications, wording fixes, typo corrections, non-semantic refinements

CLI versions (in `pyproject.toml`) also follow semantic versioning with CHANGELOG.md entries required for all changes.

## Quality Assurance

### Constitution Check Gates

Implementation plans MUST pass Phase -1 gates before proceeding:

**Simplicity Gate:**

- Using ≤3 projects?
- No future-proofing?

**Anti-Abstraction Gate:**

- Using framework directly?
- Single model representation?

**Integration-First Gate:**

- Contracts defined?
- Contract tests written?

Violations MUST be documented in the Complexity Tracking section with justification.

### Review & Acceptance Checklist

Feature specifications MUST pass these criteria:

- [ ] No `[NEEDS CLARIFICATION]` markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] User stories are prioritized and independently testable
- [ ] Edge cases documented
- [ ] Non-functional requirements specified

### Infrastructure Quality Standards

For Azure infrastructure (Bicep templates):

- Learnings database (`.specify/learnings/bicep-learnings.md`) MUST exist before generation
- Missing learnings database triggers HALT behavior (Principle III)
- Architectural compliance validated via `scripts/bicep_validate_architecture.py`
- 8 critical patterns enforced (Private Endpoints, Managed Identity, TLS 1.2+, etc.)
- Validation workflow tests end-to-end deployments in test environments

## Governance

### Constitutional Authority

This constitution supersedes all other development practices. When conflicts arise between this constitution and other documentation, the constitution takes precedence.

### Amendment Process

Modifications to this constitution require:

1. **Explicit documentation** of rationale for change
2. **Review and approval** by project maintainers (@localden, @jflam)
3. **Version increment** following semantic versioning rules
4. **Backwards compatibility assessment** and migration plan if breaking
5. **Update of Sync Impact Report** at top of this file
6. **Propagation to dependent artifacts** (templates, documentation)

### Compliance Verification

All pull requests and code reviews MUST verify constitutional compliance:

- Specifications follow template structure
- Tests written before implementation
- Phase -1 gates passed or violations justified
- User stories independently testable
- Documentation updated

### Complexity Justification

Any deviation from constitutional principles (particularly Principle IV: Modular Architecture) MUST be explicitly documented in implementation plans under "Complexity Tracking" with:

- Clear statement of which principle is violated
- Detailed justification for why the complexity is necessary
- Evidence that simpler alternatives were considered and rejected

### Living Document

This constitution is a living document that evolves based on real-world experience. The amendment history below demonstrates how principles are refined while maintaining core stability:

**Amendment History:**

- 2025-11-19: Initial constitution established (v1.0.0)
- 2025-11-19: Added Development Philosophy section covering core philosophy, error handling, development approach, best practices, and collaboration guidelines (v1.1.0)

**Version**: 1.1.0 | **Ratified**: 2025-11-19 | **Last Amended**: 2025-11-19
