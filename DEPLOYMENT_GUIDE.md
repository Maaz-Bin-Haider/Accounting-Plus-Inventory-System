# Deployment Guide - Dockerized Stack on New AWS EC2 (ARM)

Complete, step-by-step guide for deploying the Accounting Plus Inventory
System on the new EC2 instance with **all company data migrated exactly**.

**Target environment**

| Item | Value |
| --- | --- |
| Instance type | `t4g.large` (ARM64 / AWS Graviton2, 2 vCPU, 8 GB RAM) |
| Storage | 20 GB gp3 |
| Elastic IP | `13.232.33.250` |
| OS | Ubuntu Server 24.04 LTS **(64-bit ARM)** |
| Stack | Docker Compose: nginx + gunicorn/Django + PostgreSQL 16 + Redis 7 |

**What runs where**

```
Browser ── port 80 ──> [nginx container]
                          |-- /static/*  -> served directly (shared volume)
                          |-- everything -> [web container: gunicorn + Django]
                                               |-- SQL    -> [db container: PostgreSQL 16]
                                               |-- cache  -> [redis container: Redis 7]
Data persists in the named Docker volume `pgdata` (survives restarts/rebuilds).
```

The whole stack was built and verified end-to-end on ARM64 with the real
production dump before writing this guide: restore works, `production_fixes.sql`
applies cleanly, the app serves pages through nginx, and Redis caching is
active (dashboard queries drop from ~45 ms to ~0.1 ms on cache hits).

> **CI/CD transition:** Parts 4 and 6 document the original manual deployment
> process. Do not use them for a new release once the approval-gated workflow is
> complete; the server will load the already-tested, commit-tagged image instead
> of pulling source and rebuilding it. The database backup and SQL-patch safety
> requirements remain mandatory.

## Configure the GitHub production approval gate

This one-time repository setting cannot be created by the workflow itself:

1. Open the GitHub repository and select **Settings -> Environments**.
2. Create an environment named exactly `production`.
3. Under deployment protection rules, enable **Required reviewers** and select
   your own GitHub account. Do not enable self-review prevention for this
   solo-developer workflow.
4. Save the protection rules. Do not add EC2 credentials yet.

After the workflow commit is pushed, the `test` and
`build-production-image` jobs must finish before `authorize-production` asks
for approval. Approve the pending deployment from the workflow run. The job
then downloads that run's exact `production-image-<commit SHA>` artifact,
verifies its SHA-256 checksum and metadata, loads it, and confirms both ARM64
architecture and the embedded commit revision. At this stage it performs no
EC2 connection and changes no production state.

### Configure production connection values

Add these under **Settings -> Environments -> production**. Use environment
secrets—not repository variables or committed files—for sensitive values:

| Type | Name | Value |
| --- | --- | --- |
| Secret | `PRODUCTION_HOST` | EC2 hostname or Elastic IP |
| Secret | `PRODUCTION_USER` | SSH account, normally `ubuntu` |
| Secret | `PRODUCTION_SSH_KEY` | Complete private key, including header/footer |
| Secret | `PRODUCTION_KNOWN_HOSTS` | Verified SSH known-hosts entry for the EC2 host |
| Variable | `PRODUCTION_PATH` | Absolute existing project path on EC2 |

Obtain the host public key from a trusted source and compare its fingerprint
with the key presented during an already trusted SSH connection. Do not disable
strict host-key checking and do not generate `known_hosts` blindly inside CI.
For the layout in this guide, `PRODUCTION_PATH` is:

```text
/home/ubuntu/Accounting-Plus-Inventory-System
```

The next workflow run performs a read-only SSH preflight after approval. It
requires an ARM64 host, a working Docker daemon and Compose plugin, a readable
production `.env`, and a valid existing Compose configuration. It neither
uploads files nor starts, stops, or modifies containers.

### Immutable production Compose override

Automated releases combine `docker-compose.yml` with
`docker-compose.deploy.yml`. The override removes `build: .` from the web
service and requires an explicit `RELEASE_IMAGE` value. It must always be the
full approved commit tag:

```bash
RELEASE_IMAGE=financee:<40-character-commit-SHA> \
  docker compose -f docker-compose.yml -f docker-compose.deploy.yml config
```

The deployment command must use the same two files and `--no-build`. A missing
`RELEASE_IMAGE` is an error, and no deployment code may supply `latest`.

### Commit-specific release staging

After approval and the read-only preflight, the workflow checks that EC2 has at
least twice the image archive size available. It creates this private directory:

```text
<PRODUCTION_PATH>/releases/<full-commit-SHA>/
```

The workflow copies only `production-image.tar`, `image-metadata.txt`, and the
deployment Compose override into it. EC2 recomputes the archive checksum before
loading the image, checks its ARM64 architecture and embedded revision, and
renders the merged Compose configuration. The success message is:

```text
Release <commit SHA> staged and verified; running containers were not changed.
```

Staging adds the image to Docker's local image store but does not recreate,
restart, stop, or otherwise modify the running production containers.

### Mandatory pre-deployment backup

Before any live release change, the approved workflow creates this PostgreSQL
custom-format backup directly on EC2:

```text
<PRODUCTION_PATH>/backups/predeploy-<full-commit-SHA>.dump
```

The dump streams from the running database container to a temporary host file.
It is accepted only when non-empty and `pg_restore --list` can read it; it is
then atomically renamed, locked to mode 0600, and accompanied by a SHA-256 file.
Every run rechecks that checksum and requires a nontrivial restore manifest.
Rerunning the same commit validates and reuses its existing backup.

The exact tested `production_fixes.sql` is also copied to the commit-specific
release directory and checked against the runner's SHA-256. It is staged only—
this milestone does not execute the patch. The expected backup success line is:

```text
Verified PostgreSQL backup predeploy-<commit SHA>.dump (... manifest lines); production was not changed.
```

### Preserve the running rollback image

After backup verification, the workflow resolves the actual image ID of the
running Compose `web` container. It refuses to continue if the container is
missing or stopped, then creates this Docker tag without restarting anything:

```text
financee:rollback-before-<new-release-commit-SHA>
```

The tag is verified against the original image ID. Container ID, image ID,
existing revision label (if any), rollback tag, and UTC capture time are saved
as mode-0600 `rollback-metadata.txt` inside the commit-specific release
directory. This remains the rollback target even when the original image had
only a Compose-generated name or no Git revision label.

### Automatic transactional SQL patch

The next step changes production database definitions. It first rechecks the
commit-specific backup checksum, then creates the minimal
`deployment_meta.sql_patches` ledger if needed. The staged patch is executed by
the database container's `psql` with `ON_ERROR_STOP`; the patch's own
`BEGIN`/`COMMIT` boundary means any SQL error rolls back all function changes.

Patch output, including the five diagnostics, is stored as mode-0600
`production-fixes.log` in the release directory. Successful execution must
contain `production_fixes.sql applied successfully.` before the workflow records
the SHA-256, source commit, backup filename, and application time in PostgreSQL.
If that checksum is already recorded, the patch is not reapplied. A failure
stops the workflow before any container restart.

### Live release, health checks, and rollback

The final approved step uses the merged Compose files with `--no-build` to
recreate only `web` and `nginx`; PostgreSQL and Redis remain running. For up to
three minutes it requires all of the following:

- the web container is running and Docker reports it healthy;
- the container's immutable image ID equals the approved commit image;
- `http://127.0.0.1/health/` returns exactly `{"status": "ok"}`.

Success writes mode-0600 `deployment-result.txt` in the release directory and
atomically updates `<PRODUCTION_PATH>/.deployed-commit`. If startup or health
fails, Compose immediately recreates `web` and `nginx` using the preserved
rollback tag and applies the same checks. A healthy rollback still fails the
GitHub job so the bad release cannot appear successful. If rollback also fails,
the workflow prints a critical error and current Compose status for recovery.

Public Cloudflare smoke checks are intentionally deferred. Cloudflare currently
returns HTTP 403 to both EC2-originated and GitHub-hosted automated requests,
while ordinary external requests return 200. Re-enable public monitoring only
after adding a narrow Cloudflare rule for the health endpoint; do not weaken
site-wide bot or security protections merely to satisfy CI.

---

## Part 0 - Before you start (checklist)

- [ ] All users are stopped from making entries on the old system (done, per your note).
- [ ] You can SSH to the old EC2 instance (to take one final fresh dump).
- [ ] The new elastic IP `13.232.33.250` is allocated in the **new region** and not yet attached, or attached to the new instance.
- [ ] Your SSH key pair for the new region is downloaded (`.pem` file).
- [ ] The latest code (including the `Dockerfile`, `docker-compose.yml`, `docker/` folder, `production_fixes.sql`) is pushed to GitHub by you.

> **Important:** the database dump contains all company data and password
> hashes. It is now in `.gitignore` - transfer it with `scp`, never through
> GitHub.

---

## Part 1 - Take the FINAL dump from the old EC2

Even though users are stopped, take one fresh dump at migration time so the
new server is guaranteed byte-exact with the old database.

SSH into the **old** instance and run:

```bash
pg_dump -h localhost -U <OLD_DB_USER> -d <OLD_DB_NAME> > ~/db_backup_final.sql
# quick sanity check - should show table COPY blocks and functions:
grep -c "^COPY" ~/db_backup_final.sql
```

Download it to your Mac:

```bash
scp -i <old-key.pem> ubuntu@<OLD_EC2_IP>:~/db_backup_final.sql ~/Downloads/db_backup_final.sql
```

If you cannot reach the old instance any more, use the local
`db_backup_20260718_0000.sql` - you confirmed it is the latest full backup.
Everything below works identically with either file; the guide calls the file
`db_backup_final.sql`.

**Do not terminate the old instance yet.** Stop it, keep it until Part 8
verification is complete. It is your rollback.

---

## Part 2 - Launch the new EC2 instance

In the AWS console (new region):

1. **EC2 -> Launch instance**
2. Name: `financee-production`
3. AMI: **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type - 64-bit (ARM)**
   - Must be the **ARM** image, because `t4g.large` is Graviton (aarch64).
4. Instance type: `t4g.large`
5. Key pair: select/create one for this region; download the `.pem`.
6. Network settings -> **Security group** (create new, e.g. `financee-sg`):
   | Type | Port | Source | Purpose |
   | --- | --- | --- | --- |
   | SSH | 22 | *My IP* (your office/home IP only) | admin access |
   | HTTP | 80 | 0.0.0.0/0 | the application |
   - Do **NOT** open 5432 (PostgreSQL) or 6379 (Redis). They stay inside the
     Docker network and are never exposed.
7. Storage: **20 GB gp3** (that is plenty: image + containers ~2 GB, database
   ~1 GB, leaves lots of room for backups).
8. Launch.
9. **Elastic IP:** EC2 -> Elastic IPs -> select `13.232.33.250` ->
   *Associate Elastic IP address* -> choose the new instance.

Verify from your Mac:

```bash
ssh -i <new-key.pem> ubuntu@13.232.33.250
```

---

## Part 3 - Install Docker on the new instance

Run on the new instance (all commands as the default `ubuntu` user):

```bash
# 1. System update
sudo apt-get update && sudo apt-get upgrade -y

# 2. Docker's official repository (supports arm64)
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# 3. Install Docker Engine + Compose plugin
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Run docker without sudo
sudo usermod -aG docker ubuntu
# log out and back in for the group to apply:
exit
```

Reconnect and verify:

```bash
ssh -i <new-key.pem> ubuntu@13.232.33.250
docker --version          # Docker version 2x.x
docker compose version    # Docker Compose version v2.x
docker run --rm hello-world
```

Docker's service is enabled by default, and every container in
`docker-compose.yml` has `restart: unless-stopped`, so the whole stack comes
back automatically after a reboot.

---

## Part 4 - Get the code and data onto the server

```bash
# On the new instance
cd ~
git clone https://github.com/<your-account>/<your-repo>.git Accounting-Plus-Inventory-System
cd Accounting-Plus-Inventory-System
mkdir -p backups
```

Copy the database dump from your Mac (separate terminal, on your Mac):

```bash
scp -i <new-key.pem> ~/Downloads/db_backup_final.sql \
    ubuntu@13.232.33.250:~/Accounting-Plus-Inventory-System/db_backup_final.sql
```

---

## Part 5 - Create the production .env

On the new instance, in the project folder:

```bash
cp .env.example .env
nano .env
```

Set it exactly like this (choose your own strong values for the two secrets):

```ini
# Security
SECRET_KEY=<paste a NEW long random string - command below>
DEBUG=False

ALLOWED_HOSTS=13.232.33.250,localhost,127.0.0.1

# Database - MUST use DB_USER=postgres because the dump assigns object
# ownership to the postgres role.
DB_NAME=financee
DB_USER=postgres
DB_PASSWORD=<strong password - this creates the postgres superuser in the container>
DB_HOST=localhost
DB_PORT=5432

# Leave empty here; docker-compose overrides it to redis://redis:6379/1
REDIS_URL=

# Dashboard cache TTL in seconds (0 disables dashboard caching)
DASHBOARD_CACHE_SECONDS=60
```

Generate a fresh SECRET_KEY:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Notes:

- `DB_HOST`/`DB_PORT`/`REDIS_URL` in `.env` only matter for running Django
  *outside* docker; inside the stack, compose overrides them to `db:5432`
  and `redis://redis:6379/1` automatically.
- Do NOT reuse the old server's SECRET_KEY. Changing it only invalidates
  password-reset links and signed cookies; logins and data are unaffected.
- Lock the file down: `chmod 600 .env`

---

## Part 6 - Build and start the stack

```bash
cd ~/Accounting-Plus-Inventory-System
docker compose build          # builds the web image on ARM (~2-4 minutes)
docker compose up -d          # starts db, redis, web, nginx
docker compose ps             # wait until db/redis/web show (healthy)
```

On the very first start, the `db` container initializes an **empty** database
named `financee` owned by `postgres` with your `DB_PASSWORD`. The web
container waits for it, runs `collectstatic`, and starts gunicorn with 3
workers. At this point the app is up but the database is empty - do the
restore next.

---

## Part 7 - Restore all company data + apply the fix patch

### 7.1 Restore the dump

```bash
cd ~/Accounting-Plus-Inventory-System
docker compose exec -T db psql -U postgres -d financee -v ON_ERROR_STOP=1 < db_backup_final.sql
```

This takes well under a minute. `ON_ERROR_STOP=1` makes any error abort
loudly instead of continuing silently. (If you ever need to re-run a restore
from scratch: `docker compose down`, `docker volume rm financee_pgdata`,
`docker compose up -d`, then restore again.)

### 7.2 Apply the stored-procedure fixes

The dump contains the OLD buggy functions (it was taken before the fixes), so
apply the one-time patch on top:

```bash
docker compose exec -T db psql -U postgres -d financee < production_fixes.sql
```

Expected output ends with `production_fixes.sql applied successfully.` and
five read-only diagnostics.

### 7.3 Review the diagnostics - KNOWN DATA NOTES

When this was tested against the July 18 production dump:

- Diagnostics 2, 3, 4 returned **0 rows** (clean).
- Diagnostic 5 showed total debits = total credits (books balance).
- **Diagnostic 1 listed 3 serials** with more than one active "Sold" record -
  real historical corruption created while the old bugs were live:

  | Serial | What happened | Detail |
  | --- | --- | --- |
  | `352355700564521` | Listed **twice on the same invoice 373** (SHEHZAD MUGHAL, 2026-03-01). The invoice line bills qty 7 at 3615.00 but only 6 physical units left stock. | Decide: if only 6 units were delivered, edit invoice 373 in the app (now validated) to the correct serial list, which fixes billing and stock; if 7 were delivered, one unit's serial was never recorded. |
  | `353938643115292` | Sold on invoice 166 (RAAD AL MADINA, 2026-01-27) and again on invoice 194 (MUDASSIR, 2026-01-31). The sale return between them was later deleted/updated by the old buggy code, which re-activated both sales. | Check both customers' ledgers, then mark the superseded sale record as returned: `UPDATE soldunits SET status='Returned' WHERE sold_unit_id=<3225 for inv 166 or 3160 for inv 194>;` |
  | `4V0ZW23H7303H1` | Sold on invoice 359 (POWER PLAY, 2026-02-25) and again on invoice 414 (POWER PLAY, 2026-03-09). Same cause. | Same customer both times - mark the earlier sale's record as returned: `UPDATE soldunits SET status='Returned' WHERE sold_unit_id=<7309 for inv 359 or 7109 for inv 414>;` |

  Nothing is auto-repaired: these need a business decision (which sale is the
  real one / how the money was settled). The system runs fine meanwhile; the
  new validations prevent any NEW corruption of this kind. After you decide,
  run the one-line UPDATE for each serial inside
  `docker compose exec db psql -U postgres -d financee`.

### 7.4 Restart the web container

Restart once after the restore so every worker starts from a clean
connection state:

```bash
docker compose restart web
```

---

## Part 8 - Verify the migration

### 8.1 Data is exactly there

```bash
docker compose exec db psql -U postgres -d financee -c "
SELECT 'parties' t, count(*) FROM parties UNION ALL
SELECT 'items', count(*) FROM items UNION ALL
SELECT 'purchaseinvoices', count(*) FROM purchaseinvoices UNION ALL
SELECT 'salesinvoices', count(*) FROM salesinvoices UNION ALL
SELECT 'purchaseunits', count(*) FROM purchaseunits UNION ALL
SELECT 'soldunits', count(*) FROM soldunits UNION ALL
SELECT 'payments', count(*) FROM payments UNION ALL
SELECT 'receipts', count(*) FROM receipts UNION ALL
SELECT 'journalentries', count(*) FROM journalentries UNION ALL
SELECT 'journallines', count(*) FROM journallines UNION ALL
SELECT 'auth_user', count(*) FROM auth_user;"
```

Compare with the same query on the old server (or with the reference counts
from the July 18 dump: parties 231, items 265, purchaseinvoices 199,
salesinvoices 874, purchaseunits 9283, soldunits 8261, payments 1504,
receipts 1736, journalentries 4610, journallines 11038, auth_user 8).

Also check the books balance:

```bash
docker compose exec db psql -U postgres -d financee -c \
  "SELECT sum(debit) AS debits, sum(credit) AS credits FROM journallines;"
```

### 8.2 Application works

From your browser: **http://13.232.33.250**

- [ ] Redirects to the login page with proper styling (static files OK).
- [ ] Log in with an existing user (all users/passwords migrated unchanged).
- [ ] Dashboard loads with real numbers.
- [ ] Open Sales, navigate previous/next invoices, view a PDF.
- [ ] Try an invalid entry (e.g. sale return of an in-stock serial) - you get
      the new descriptive error message.
- [ ] Reports: trial balance, stock report, ledgers.

### 8.3 Redis cache is working

```bash
docker compose exec redis redis-cli -n 1 dbsize   # grows after you open the dashboard
docker compose exec redis redis-cli info stats | grep keyspace
```

### 8.4 Survives a reboot

```bash
sudo reboot
# reconnect after ~1 minute
ssh -i <new-key.pem> ubuntu@13.232.33.250
docker compose ps    # all four containers Up again, data intact
```

Once everything checks out, keep the old instance **stopped** for a week or
two as a safety net, then terminate it.

---

## Part 9 - Automatic daily backups

On the new instance:

```bash
crontab -e
```

Add these two lines (daily dump at 00:00 server time, keep 14 days):

```cron
0 0 * * * cd /home/ubuntu/Accounting-Plus-Inventory-System && docker compose exec -T db pg_dump -U postgres -d financee > backups/db_backup_$(date +\%Y\%m\%d_\%H\%M).sql 2>> backups/backup.log
30 0 * * * find /home/ubuntu/Accounting-Plus-Inventory-System/backups -name 'db_backup_*.sql' -mtime +14 -delete
```

Each dump is ~4 MB, so 14 days uses ~60 MB of the 20 GB disk.
Strongly recommended: copy backups off the instance periodically, e.g. to S3:

```bash
# one-time: create a bucket + attach an instance role with s3:PutObject, then:
aws s3 cp backups/ s3://<your-backup-bucket>/financee/ --recursive --exclude '*' --include 'db_backup_*.sql'
```

Restoring from a backup (disaster recovery):

```bash
docker compose down
docker volume rm financee_pgdata
docker compose up -d db
sleep 10
docker compose exec -T db psql -U postgres -d financee -v ON_ERROR_STOP=1 < backups/<backup-file>.sql
docker compose up -d
```

(Backups taken AFTER the patch already contain the fixed functions - no need
to re-apply `production_fixes.sql` when restoring those.)

---

## Part 10 - Day-to-day operations

| Task | Command (from `~/Accounting-Plus-Inventory-System`) |
| --- | --- |
| Status | `docker compose ps` |
| App logs (live) | `docker compose logs -f web` |
| nginx logs | `docker compose logs -f nginx` |
| DB shell | `docker compose exec db psql -U postgres -d financee` |
| Redis shell | `docker compose exec redis redis-cli -n 1` |
| Restart app only | `docker compose restart web` |
| Restart everything | `docker compose restart` |
| Stop / start stack | `docker compose down` / `docker compose up -d` (data persists) |
| Clear the cache | `docker compose exec redis redis-cli -n 1 flushdb` (harmless; users stay logged in) |
| Disk usage | `df -h` and `docker system df` |
| Clean old images | `docker image prune -f` |

**Deploying a code update** (your usual flow, dockerized):

```bash
# you push to GitHub from your Mac, then on the server:
cd ~/Accounting-Plus-Inventory-System
git pull
docker compose build web
docker compose up -d web        # rebuilds and replaces only the web container
```

**Applying a future SQL patch:**

```bash
docker compose exec -T db psql -U postgres -d financee < <patch-file>.sql
docker compose restart web
```

---

## Part 11 - Troubleshooting

| Symptom | Check / fix |
| --- | --- |
| Browser cannot reach http://13.232.33.250 | Security group allows port 80 from 0.0.0.0/0; elastic IP is associated; `docker compose ps` shows nginx Up. |
| `Bad Request (400)` in browser | `ALLOWED_HOSTS` in `.env` must contain `13.232.33.250`; then `docker compose restart web`. |
| CSRF error on login POST | Access the site as `http://13.232.33.250` (the IP in ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS), not via some other hostname. |
| web container restart-looping | `docker compose logs web` - most common causes: `.env` missing/typo, db not healthy yet. |
| Restore fails with role errors | You set `DB_USER` to something other than `postgres`. Recreate: set `DB_USER=postgres` in `.env`, `docker compose down`, `docker volume rm financee_pgdata`, `docker compose up -d`, restore again. |
| Static files 404 | `docker compose logs web | grep collectstatic` - collectstatic runs on every web start; `docker compose restart web` regenerates them. |
| Slow dashboard | Confirm Redis: `docker compose exec redis redis-cli -n 1 dbsize` should be > 0 after loading the dashboard. |
| Disk filling up | Old images/backups: `docker image prune -f`, prune old files in `backups/`. |

---

## Part 12 - Security notes

- PostgreSQL and Redis are reachable **only** inside the Docker network -
  nothing but nginx:80 is exposed to the internet. Keep it that way.
- SSH (22) is restricted to your IP in the security group.
- `DEBUG=False` always in production.
- The `.env` file and `backups/` directory never go into git.
- When you later get a domain, point it at 13.232.33.250, add the domain to
  `ALLOWED_HOSTS`, and you can add free HTTPS by putting certbot/Let's
  Encrypt in front (nginx config is ready to be extended with a 443 server
  block).

---

## Appendix - What changed in the codebase for Docker + Redis

| File | Purpose |
| --- | --- |
| `Dockerfile` | ARM-compatible web image: python:3.12-slim, gunicorn (3 workers x 2 threads), non-root user |
| `docker-compose.yml` | 4 services (db=postgres:16 matching the dump's 16.14, redis:7-alpine with 256 MB LRU cap, web, nginx), healthchecks, named volume `pgdata`, `restart: unless-stopped` |
| `docker/entrypoint.sh` | Waits for PostgreSQL, runs `collectstatic`, starts gunicorn |
| `docker/nginx.conf` | Serves `/static/` directly, proxies the rest to gunicorn |
| `.env.example` | Template for the production `.env` |
| `.dockerignore` | Keeps dumps, venvs, git history out of the image |
| `financee/settings.py` | `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` from env; Redis cache when `REDIS_URL` is set (in-memory fallback otherwise); `cached_db` sessions; `DASHBOARD_CACHE_SECONDS` (default 60); `CONN_MAX_AGE=60` |
| `home/views.py` | Dashboard DB calls cached in Redis for `DASHBOARD_CACHE_SECONDS` (accounting screens are never cached) |
| `requirements.txt` | Added `gunicorn`, `redis`; pinned Django to 5.2.x |
| `.gitignore` | Excludes `db_backup_*.sql`, `backups/`, `staticfiles/` |
