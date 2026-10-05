---
name: implement
description: "Implement a piece of work based on a spec or ticket by delegating code authoring and testing to Google Jules."
disable-model-invocation: true
---

# Implement

Delegate the implementation of the work described in the spec or ticket to Google Jules (`jules.google`).

The local harness acts as the **Architect and Planner**: it formulates the task prompt, dispatches to Jules, and verifies the resulting Pull Request. The local harness never creates or edits source code or test files directly in the repository.

## Two-Phase Jules Execution Protocol

Every implementation follows a mandatory two-phase Jules cloud pipeline:

### 1. Phase 1: Jules Coder Agent Dispatch

1. **Extract Requirements:**
   - Gather acceptance criteria, targeted seams, and verification test commands from the ticket or spec.
   - Consult `AGENTS.md` and `docs/agents/domain.md` for project conventions and glossary terms.

2. **Construct the Jules Implementation Prompt:**
   Package the prompt incorporating the red-green TDD contract from `/tdd`:
   - Declare the target seams and modules to modify.
   - Instruct Jules to write the failing automated test first in its Cloud VM.
   - Instruct Jules to write the minimal implementation to pass the test.
   - Mandate running the project test suite in the VM before creating the PR.

3. **Dispatch via Bridge Script:**
   ```bash
   node scripts/jules.mjs dispatch --prompt "<packaged-prompt>" --title "<ticket-title>"
   ```

4. **Monitor via Watcher Subagent:**
   Launch a background watcher subagent to wait on the session:
   ```bash
   node scripts/jules.mjs wait <session-id>
   ```
   The main conversation remains unblocked for discussion or planning while Jules builds in the cloud.

### 2. Phase 2: Mandatory Jules Tester Agent

As soon as the Coder Agent completes and opens a Pull Request:

1. **Extract PR Branch:** Retrieve the PR branch from the completed session output (`node scripts/jules.mjs pr <session-id>`).
2. **Dispatch Tester Agent:**
   Launch the secondary Jules Tester Agent targeting the PR branch:
   ```bash
   node scripts/jules.mjs dispatch-tester --pr-branch "<pr-branch>" --prompt "Inspect the diff on this branch. Author adversarial, boundary, and regression tests to verify that the implementation is robust, handles edge cases, and introduces no regressions. Run all tests in the VM."
   ```
3. **Wait for Tester Completion:**
   Monitor the Tester Agent session until it reaches completion.

### 3. Phase 3: Local Verification and Landing

1. **Fetch and Verify Locally:**
   The watcher subagent fetches the verified PR branch:
   ```bash
   git fetch origin pull/<pr-number>/head:pr-<pr-number>
   ```
   Run project test suites, linters, and typechecks in read-only mode to confirm green status.

2. **Landing Decision:**
   - **Routine / Scoped Changes:** If all tests pass, the diff touches 5 or fewer files, and changes are scoped to the ticket, merge the PR automatically:
     ```bash
     gh pr merge <pr-number> --squash --delete-branch --auto
     ```
   - **Major Milestones or Spec Completions:** Prepare an Executive Summary for the user:
     - What was built and why.
     - PR link and diff statistics.
     - Test verification proof and assertions confirmed by both Jules agents.
     - Request user approval before final merge.
