---
name: implement-spec
description: "Orchestrate the implementation of a full spec across its ticket graph by dispatching parallel Google Jules sessions."
disable-model-invocation: true
---

# Implement Spec

Orchestrate the end-to-end implementation of a specification and its associated tickets using Google Jules (`jules.google`).

The local harness acts as the **Task Graph Orchestrator and Verifier**: it manages the frontier of unblocked tickets, dispatches parallel Jules Coder and Tester sessions, merges verified PRs onto an integration branch, and presents an executive summary upon completion. The local harness never directly writes or edits code in the repository.

The tickets form a **task graph** with blocking edges. At any moment, there is a **frontier** of tickets whose blockers are closed and which are ready to be implemented.

## Orchestration Workflow

### 1. Initialize Integration Branch
Create the dedicated integration branch for the spec (e.g. `spec/<spec-name>`):
```bash
git checkout -b spec/<spec-name> main
git push -u origin spec/<spec-name>
```

### 2. Identify the Ready Frontier
Query the tickets to find all tickets whose dependencies are satisfied. These tickets form the active frontier.

### 3. Dispatch Jules Sessions Concurrently
For each unblocked ticket on the frontier (up to your plan concurrency limit):
1. **Prepare Prompt:** Construct the prompt specifying the ticket requirements, acceptance criteria, and TDD discipline from `/tdd`.
2. **Dispatch Coder Agent:** Target the spec integration branch as the starting branch:
   ```bash
   node scripts/jules.mjs dispatch --prompt "<prompt>" --title "<ticket-title>" --branch spec/<spec-name>
   ```
3. **Launch Watcher Subagent:** Spin up a background watcher subagent to monitor the session via `node scripts/jules.mjs wait <session-id>`.

### 4. Mandatory Jules Tester Agent on Every PR
When a Coder Agent opens a PR for a ticket:
1. The watcher subagent immediately launches the Jules Tester Agent on that PR branch:
   ```bash
   node scripts/jules.mjs dispatch-tester --pr-branch "<pr-branch>" --prompt "Inspect the diff for ticket <ticket-name>. Author comprehensive edge-case, boundary, and regression tests. Verify the full test suite in the VM."
   ```
2. The watcher waits for the Tester Agent to reach completion.

### 5. Verify and Merge into Integration Branch
1. The watcher checks out the verified PR branch locally and runs project test suites and linters in read-only mode.
2. If tests pass, merge the PR into the `spec/<spec-name>` integration branch.
3. Close the corresponding ticket on the issue tracker.

### 6. Advance the Frontier
Closing completed tickets unblocks downstream dependent tickets. Dispatch new Jules Coder + Tester sessions for newly unblocked tickets. Repeat until all tickets in the spec task graph are resolved.

### 7. Final Spec Verification and Executive Summary
Once all tickets across the graph are complete:
1. Call `/code-review` over the entire integration branch diff against `main`.
2. Run the complete test suite locally to verify full integration health.
3. Prepare an **Executive Summary** for the user:
   - Overview of the spec capabilities delivered.
   - Complete table of closed tickets and PR links.
   - Comprehensive test verification report from all Jules Coder and Tester sessions.
4. Present the summary to the user for one-click approval to merge `spec/<spec-name>` into `main`.
