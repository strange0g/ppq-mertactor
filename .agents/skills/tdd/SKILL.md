---
name: tdd
description: Test-driven development specification. Use when defining the red-green testing discipline to mandate in Google Jules implementation prompts.
---

# Test-Driven Development (Jules Prompt Specification)

TDD is the red → green loop. Because all code authoring is delegated to Google Jules (`jules.google`), this skill serves as the **authoritative specification for prompt engineering**: it dictates how the local harness must instruct Jules to build test-first.

The local harness never writes test or production files directly in the repository. Instead, it embeds the strict rules of this skill into every task prompt sent to the Jules Coder Agent.

When preparing prompts, read `GLOSSARY.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area being modified.

## What a Good Test Is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests should survive refactors. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: Where Tests Go

A **seam** is the public boundary tested at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before dispatching to Jules, identify the seams under test from the ticket and explicitly name them in the Jules prompt:
- Declare the public interface under test.
- Instruct Jules to write tests against that seam, never against private methods.

When the shape of that interface is in question (module depth, where the seam belongs), consult `/codebase-design` for vocabulary.

## Anti-Patterns to Forbid in Jules Prompts

Prompts sent to Jules must explicitly forbid these common pitfalls:
- **Implementation-coupled:** mocking internal collaborators, testing private methods, or verifying through side channels.
- **Tautological:** assertions that recompute the expected value the same way the code does. Expected values must come from an independent source of truth (known-good literals or spec fixtures).
- **Horizontal slicing:** writing speculative bulk tests without working vertical slices.

## Mandatory TDD Rules for Jules Prompts

Every implementation prompt dispatched via `scripts/jules.mjs` must instruct Jules to adhere to the following contract:

1. **Red before green:** Write the failing test first in the Cloud VM. Execute the project test command and verify that the test fails for the expected reason before writing any production code.
2. **Minimal implementation:** Write only enough production code to turn the failing test green. Do not anticipate unrequested features.
3. **In-VM verification:** Run the full project test suite in the Cloud VM to confirm all existing and new tests pass before opening the Pull Request.
4. **Followed by Jules Tester Agent:** All PRs opened by the Coder Agent will immediately undergo a secondary pass by the Jules Tester Agent to author boundary and adversarial tests.
