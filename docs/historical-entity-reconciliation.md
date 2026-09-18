# Historical Jolpica entity reconciliation

Historical Jolpica ingestion must not require one registry migration per season.

## Flow

```text
season calendar
season drivers
season constructors
latest season driver standings
        |
        v
canonical reconciliation
        |
        +-- exact provider ID
        +-- provider validity extension
        +-- exact canonical identity
        +-- auto-create historical entity
        +-- ambiguous -> audit + fail before results ingestion
        |
        v
entity_provider_ids
team_person_roles
entity_reconciliation_audit
        |
        v
race / qualifying / sprint / standings ingestion
```

## Driver identity policy

Resolution order:

1. Exact Jolpica provider ID already mapped.
2. Extend that provider mapping's validity to the requested season.
3. Exact normalized full-name match against one canonical driver, with birth-date conflict protection when both dates are known.
4. Create a new historical driver entity/person and canonical aliases.

Fuzzy name matching is intentionally not used.

## Constructor identity policy

Resolution order:

1. Exact Jolpica constructor provider ID already mapped.
2. Extend that provider mapping's validity.
3. Exact normalized constructor-name match against one canonical team.
4. Create a distinct historical constructor entity.

Constructor successor/predecessor relationships are not inferred. A provider identity such as Sauber is not silently rewritten as Audi, and historical rebrands can later be connected by an explicit lineage model if desired.

## Ambiguity

When multiple exact candidates exist, or a driver full name matches but the known birth date conflicts, reconciliation writes an `ambiguous` audit row with `review_required=true` and stops structured result ingestion for that season.

This preserves the existing fail-fast behavior while making the unresolved identity visible.

## Audit

`entity_reconciliation_audit` records:

- provider and provider entity type;
- provider ID and season;
- resolved canonical entity, if any;
- resolution method;
- confidence;
- review-required state;
- source URL and metadata.

Methods are:

- `exact_provider_id`
- `provider_validity_extension`
- `exact_identity`
- `auto_created`
- `ambiguous`

## Driver-team participation

Season standings create initial driver-team roster links. Race, qualifying and Sprint rows also refresh `team_person_roles`, so mid-season transfers and substitutions can produce multiple driver-team relationships in the same season.

## Commands

Single season:

```bash
SEASON=2024 make ingest-jolpica
```

Range:

```bash
START_SEASON=2020 END_SEASON=2026 make ingest-jolpica-history
```

Reverse order is also supported by the Python runner.

Both Make targets apply replay-safe migrations before ingestion.

## Legacy 2025 migration

`029_jolpica_2025_entity_registry.sql` remains as the historical bootstrap that repaired existing databases before generic reconciliation existed. New seasons should not receive equivalent per-season migrations.
