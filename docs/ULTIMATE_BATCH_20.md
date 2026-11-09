# Ultimate B20: CI build only at release boundaries, never publish from experiments

**Purpose:** keep the full Ultimate B01–B19 cumulative source chain, including B15 five-peer Docker-verified server, B17/B18 admission fixes and B19 corrected native Windows EXE finalization, while avoiding **full Docker image builds on every incremental Draft PR**.

## Existing problem confirmed from GitHub Actions

`.github/workflows/deploy.yml` runs on every PR that changes `server/**`. Before B20 it always launched three jobs: Helm chart lint, Terraform validation, and the heavy `server/hosting/Dockerfile` plus backup Docker image builds. B17 and B18 each triggered this duplicate workflow despite having dedicated real C++ source tests and despite being Draft branches not destined for production. These unnecessary long jobs are precisely the per-patch rebuilding the project is supposed to avoid.

The existing workflow also used `push: github.event_name != 'pull_request'`, so **manual workflow_dispatch on a nonrelease branch would have attempted to publish GHCR images**. That is inconsistent with a guarded, no-release development process.

## B20 CI-only changes

- Scope Helm, Terraform and Docker image jobs to (1) pushes on the configured release branches `main` and `hosted-server`, (2) **PRs targeting** these release branches, or (3) explicit manual workflow dispatch. Draft PRs stacked on `experiment/ultimate-...` skip these jobs and rely on their own exact-parent source, native C++ and dedicated integration gates.
- Allow GHCR login and **both** `docker/build-push-action` pushes **only** for a `push` event to `refs/heads/main` or `refs/heads/hosted-server`. A manual dispatch on any branch still builds and can smoke-test locally but **does not publish**. For non-push events the shadNet image is loaded locally for the existing admin socket smoke test.
- Preserve release PR checks: full Helm values lint/templates, Terraform fmt/init/validate, shadNet Docker builder, backup image and local Docker smoke. No application, account, network, save/rollback, package or game-code modification.
- Keep `on: push`, `on: pull_request` and `workflow_dispatch` available with the original path filters; only expensive jobs are gated by intended release stage.

## Validations

`tools/ultimate/test_batch_20_release_ci_scope.py` verifies the actual workflow job scopes, GHCR login/push predicates, release/manual/staged PR truth table, and preservation of Helm/Terraform/Docker smoke. Dedicated B20 GitHub Actions checks exact **five-file B19→B20** source scope, Git blob identities, and exercises the test on Ubuntu. A normal stacked B20 PR should show the old `Deploy files` workflow as skipped, not spend resources compiling hosted Docker again.

Manual checks remain intentional actions and can incur CI costs, but do not create public releases. This affects CI only and **does not touch Fornex**. The Windows B19 native PE run remains separately required; this CI improvement is not gameplay validation or the independent real no-PS4-ELF native PC port.
