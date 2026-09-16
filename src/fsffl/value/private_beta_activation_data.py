from __future__ import annotations

import base64
import bz2
import hashlib
import json

from ._private_beta_activation_facts import BZ2_BASE64 as FACTS_BZ2_BASE64
from ._private_beta_activation_h12 import BZ2_BASE64 as H12_BZ2_BASE64
from ._private_beta_activation_h3 import BZ2_BASE64 as H3_BZ2_BASE64
from ._private_beta_activation_report import BZ2_BASE64 as REPORT_BZ2_BASE64

# Generated from successful private-beta activation workflow run 35127295366.
# Runtime consumers see provider-neutral JSON only through the frozen schemas.
ACTIVATION_WORKFLOW_RUN_ID = 35127295366
ACTIVATION_ARTIFACT_SHA256 = {
    "frozen_i1_h12.json": "6ad9d0e52235e711985a27ec6af6764268841f57188b444b857e173b7019a905",
    "frozen_i1_h3.json": "844391290ba14fc7c2ee84e1211b8963271df839b60c562214fefe757cd84b4d",
    "current_i1_facts_2026.json": "4ee0719c40dfc067c23e76d09dda8e501fa95014dbc2162d10ee571882f07edf",
    "private_beta_activation_build_report.json": "6ba83ea44546f597f0726d7c7dc9d9e4140f034b0b397e97f2501292879b9127",
}
ACTIVATION_BUNDLE_SHA256 = "e3e8e62c6fc77bb80cdce1bfc0d33472ca6e3f13ebb9094c24f54d5ccd69ac21"
_COMPRESSED_ARTIFACTS = {
    "frozen_i1_h12.json": H12_BZ2_BASE64,
    "frozen_i1_h3.json": H3_BZ2_BASE64,
    "current_i1_facts_2026.json": FACTS_BZ2_BASE64,
    "private_beta_activation_build_report.json": REPORT_BZ2_BASE64,
}


def activation_artifact_text(name: str) -> str:
    try:
        encoded = _COMPRESSED_ARTIFACTS[name]
        expected = ACTIVATION_ARTIFACT_SHA256[name]
    except KeyError as exc:
        raise ValueError(f"missing private-beta activation artifact: {name}") from exc
    raw = bz2.decompress(base64.b64decode(encoded, validate=True))
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(f"private-beta activation artifact digest mismatch: {name}")
    return raw.decode("utf-8")


def activation_manifest_digest() -> str:
    payload = json.dumps(
        ACTIVATION_ARTIFACT_SHA256,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
