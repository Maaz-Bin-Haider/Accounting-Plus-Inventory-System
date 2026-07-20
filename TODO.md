# Testing and CI/CD Roadmap

Target solo-developer flow:

```text
push to main
  -> run required CI tests
  -> build a commit-tagged Docker image
  -> request approval in the GitHub production environment
  -> deploy to EC2
  -> verify health or automatically roll back
```

Deployment must never start when a required CI check fails. Manual approval is
intentionally placed after tests and image creation.

## 1. Build a production-grade test foundation

- [x] Record the test and delivery roadmap.
- [x] Establish authentication endpoint and CSRF tests.
- [x] Establish tests for safe PostgreSQL error translation.
- [x] Add a dedicated PostgreSQL test configuration that cannot target production.
- [x] Add initial reusable helpers for users and custom permissions.
- [ ] Add reusable helpers for JSON requests and mocked DB cursors.
- [ ] Test parties and items: access, permissions, view-only restrictions, CRUD,
      duplicates, invalid payloads, autocomplete, and list contracts.
  - [x] Parties authentication, view permission, autocomplete, list, and CSRF.
  - [x] Parties create/update permission contracts, view-only group, and duplicates.
  - [ ] Parties malformed/invalid payload behavior and database error responses.
  - [x] Items authentication, permissions, create/update contracts, autocomplete,
        list serialization, CSRF, duplicates, and safe database failures.
  - [ ] Items malformed numeric/text payload validation.
- [ ] Test sales and purchases: permissions, CRUD, navigation, summaries, serial
      lookup/validation, malformed requests, and safe database failures.
  - [x] Sales page access, request validation, CSRF, navigation, serial lookup,
        bulk grouping/deduplication, and summary contracts.
  - [x] Sales validated create/update/delete execution, permissions, view-only
        restriction, description persistence, attribution, and safe failures.
  - [x] Purchases access, validated CRUD execution, permissions, descriptions,
        attribution, navigation, summaries, CSRF, and serial classification.
- [ ] Test sale and purchase returns: permissions, lifecycle rules, CRUD,
      navigation, summaries, and safe failures.
  - [x] Return page access, lookup state, create/update/delete procedure
        contracts, attribution, descriptions, navigation, summaries, and CSRF.
  - [ ] Return view-only restrictions and curated database lifecycle failures.
- [ ] Test payments, receipts, and contra entries: permissions, CRUD, navigation,
      date lookup, balances, accounting side effects, and safe failures.
  - [x] Access, CSRF, create/update payloads, navigation/date validation, balance
        contracts, contra same-party validation, and contra deletion.
  - [ ] Delete permissions for payments/receipts, view-only restrictions, old
        entry lists, successful date queries, and safe database failures.
- [ ] Test every dashboard API, permission-controlled section, parameter rule,
      cache hit/miss path, and failure response.
  - [x] Dashboard login, all section permission denials, primary function and
        parameter contracts, GET enforcement, cache enabled/disabled behavior,
        and legacy financial-data hiding.
  - [ ] Dashboard invalid numeric/date parameters and database failure responses.
- [ ] Test all account, stock, serial, profit, valuation, and monthly reports.
- [ ] Smoke-test every HTML page, template, and required static asset.
- [ ] Verify CSRF on every state-changing endpoint and prevent SQL error leakage.
- [ ] Expand PostgreSQL system tests for payment/receipt/contra accounting, party
      openings, concurrency, duplicate serials, numeric/date boundaries, return
      mutation, and report-to-journal reconciliation.
- [ ] Add regression coverage for every defect in `FIXES.md`.
- [ ] Add Docker startup, health-check, static-file, and nginx proxy smoke tests.
- [ ] Report coverage, agree a threshold, then enforce it.
- [ ] Provide separate fast-test and full-system-test commands.
- [ ] Keep all fixtures deterministic and independent of production data.

## 2. Make tests CI-ready

- [ ] Pin production and test dependencies reproducibly.
- [x] Add an isolated Docker Compose test stack with ephemeral PostgreSQL.
- [ ] Add Redis integration tests and enable Redis in the test stack when needed.
- [ ] Restore schema into a disposable DB and apply required SQL patches once.
- [x] Reject production-like database names and hosts before tests start.
- [ ] Run Django system/deployment checks, endpoint tests, and system tests.
- [ ] Publish test results and coverage as GitHub Actions artifacts.
- [ ] Cache dependencies and image layers, never test database state.

## 3. Continuous Integration for `main`

- [ ] Trigger GitHub Actions on pushes to `main` and manual dispatch.
- [ ] Run syntax, configuration, Django, endpoint, database, and system checks.
- [ ] Build the same ARM64-compatible Docker image used in production.
- [ ] Tag the image with the Git commit SHA; never deploy implicit `latest`.
- [ ] Prevent the deployment job unless every required check passes.

## 4. Approval-gated Continuous Deployment

- [ ] Create a protected GitHub Environment named `production` with the solo
      developer as required reviewer.
- [ ] Request approval only after successful CI and image creation.
- [ ] Keep secrets in the GitHub Environment and/or AWS Systems Manager, never Git.
- [ ] Deploy the already-tested commit-tagged image to EC2.
- [ ] Verify a PostgreSQL backup before changing the running release.
- [ ] Lock deployments so two releases cannot overlap.
- [ ] Preserve the previously working image tag for rollback.
- [ ] Wait for container and HTTP health checks after deployment.
- [ ] Run post-deployment smoke tests and roll back automatically on failure.
- [ ] Record the deployed commit, image tag, timestamps, and result.
- [ ] Document approval, deploy, rollback, secrets, SQL patches, and recovery.

## 5. Production readiness

- [ ] Rotate the exposed Django secret key and PostgreSQL password.
- [ ] Confirm Cloudflare SSL mode and the nginx origin-certificate configuration.
- [ ] Enable Django proxy SSL and secure-cookie settings after HTTPS is verified.
- [ ] Monitor uptime, container health, disk, backup age, errors, and PostgreSQL.
- [ ] Prove a full database restore and application rollback before relying on CD.
