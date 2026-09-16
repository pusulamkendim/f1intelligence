# Local port configuration

Local host port overrides belong in `.env`, not in tracked source files.

The repository's Docker Compose configuration exposes Redis with:

```yaml
ports:
  - "${REDIS_HOST_PORT:-6379}:6379"
```

For a machine where host port `6379` is already occupied, use:

```dotenv
REDIS_HOST_PORT=6380
REDIS_URL=redis://localhost:6380/0
```

The Redis container still listens on `6379` internally; only the host-side published port changes.

`.env` is intentionally gitignored, so `git pull` does not replace machine-specific values.

Do not edit `docker-compose.yml` solely to change a developer's local port. Keep shared defaults in `.env.example` and machine-specific overrides in `.env`.
