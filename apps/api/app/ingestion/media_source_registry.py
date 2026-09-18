from dataclasses import dataclass
from typing import Literal

SourceRole = Literal["origin", "discovery", "license_resolver"]
StoragePolicy = Literal[
    "metadata_only",
    "remote_reference",
    "cache_allowed",
    "self_host_allowed",
]
RightsStatus = Literal[
    "unknown",
    "restricted",
    "editorial_only",
    "license_required",
    "verified",
]


@dataclass(frozen=True)
class MediaSourcePolicy:
    key: str
    source_role: SourceRole
    rights_status: RightsStatus
    storage_policy: StoragePolicy
    usage_scope: str
    rights_evidence_url: str | None = None
    notes: str | None = None


MEDIA_SOURCE_POLICIES: dict[str, MediaSourcePolicy] = {
    "f1-fansite.com": MediaSourcePolicy(
        key="f1-fansite.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://www.f1-fansite.com/disclaimer/",
        notes="Discovery/index only; resolve the original photographer/agency before reuse.",
    ),
    "formula1.com": MediaSourcePolicy(
        key="formula1.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://www.formula1.com/en/information/guidelines.4EOKE9RRqevL4niTK9kWyt",
        notes="Reference/discovery only unless a separate licence is obtained.",
    ),
    "williamsf1.com": MediaSourcePolicy(
        key="williamsf1.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://www.williamsf1.com/legal",
        notes="First-party team discovery source; retain metadata only unless asset terms explicitly permit reuse.",
    ),
    "media.alpinecars.com": MediaSourcePolicy(
        key="media.alpinecars.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://media.alpinecars.com/?lang=eng",
        notes="First-party media-centre discovery source; verify asset-specific terms before reuse.",
    ),
    "redbullracing.com": MediaSourcePolicy(
        key="redbullracing.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://www.redbullracing.com/int-en",
        notes="Official Oracle Red Bull Racing portrait discovery source; publication rights remain restricted.",
    ),
    "mclaren.com": MediaSourcePolicy(
        key="mclaren.com",
        source_role="discovery",
        rights_status="restricted",
        storage_policy="metadata_only",
        usage_scope="unknown",
        rights_evidence_url="https://www.mclaren.com/racing/terms-and-conditions/",
        notes="Official McLaren team portrait discovery source; publication rights remain restricted.",
    ),
    "openf1_headshot": MediaSourcePolicy(
        key="openf1_headshot",
        source_role="discovery",
        rights_status="unknown",
        storage_policy="remote_reference",
        usage_scope="unknown",
        notes="OpenF1 exposes a URL but does not grant image reuse rights.",
    ),
    "wikimedia_commons": MediaSourcePolicy(
        key="wikimedia_commons",
        source_role="origin",
        rights_status="verified",
        storage_policy="self_host_allowed",
        usage_scope="editorial",
        notes="Asset-level licence and attribution must still be stored and enforced.",
    ),
    "red_bull_content_pool": MediaSourcePolicy(
        key="red_bull_content_pool",
        source_role="origin",
        rights_status="editorial_only",
        storage_policy="cache_allowed",
        usage_scope="editorial",
        notes="Use only within the rights attached to the specific asset.",
    ),
    "audi_media": MediaSourcePolicy(
        key="audi_media",
        source_role="origin",
        rights_status="editorial_only",
        storage_policy="cache_allowed",
        usage_scope="editorial",
        notes="Verify each asset's editorial-use notice before storage/publication.",
    ),
    "team_media": MediaSourcePolicy(
        key="team_media",
        source_role="origin",
        rights_status="unknown",
        storage_policy="metadata_only",
        usage_scope="unknown",
        notes="Team media-centre terms vary by team and asset.",
    ),
    "getty_images": MediaSourcePolicy(
        key="getty_images",
        source_role="license_resolver",
        rights_status="license_required",
        storage_policy="metadata_only",
        usage_scope="editorial",
        notes="Storage/publication depends on the purchased licence and API terms.",
    ),
    "lat_images": MediaSourcePolicy(
        key="lat_images",
        source_role="license_resolver",
        rights_status="license_required",
        storage_policy="metadata_only",
        usage_scope="editorial",
    ),
    "sutton_images": MediaSourcePolicy(
        key="sutton_images",
        source_role="license_resolver",
        rights_status="license_required",
        storage_policy="metadata_only",
        usage_scope="editorial",
    ),
    "dppi": MediaSourcePolicy(
        key="dppi",
        source_role="license_resolver",
        rights_status="license_required",
        storage_policy="metadata_only",
        usage_scope="editorial",
    ),
}


def policy_for_provider(provider: str) -> MediaSourcePolicy:
    return MEDIA_SOURCE_POLICIES.get(
        provider,
        MediaSourcePolicy(
            key=provider,
            source_role="discovery",
            rights_status="unknown",
            storage_policy="metadata_only",
            usage_scope="unknown",
            notes="Unknown provider; retain metadata only until rights are verified.",
        ),
    )
