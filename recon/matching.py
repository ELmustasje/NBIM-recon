"""Record matching between NBIM and custodian datasets."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .models import DividendRecord, MatchKey


class MatchResult:
    """Container for matched and unmatched dividend records."""

    def __init__(self) -> None:
        self.pairs: Dict[MatchKey, Tuple[DividendRecord |
                                         None, DividendRecord | None]] = {}

    def add_pair(
        self,
        key: MatchKey,
        nbim: DividendRecord | None,
        custodian: DividendRecord | None,
    ) -> None:
        self.pairs[key] = (nbim, custodian)

    def items(self):
        return self.pairs.items()


def match_records(nbim: Iterable[DividendRecord], custodian: Iterable[DividendRecord]) -> MatchResult:
    result = MatchResult()

    nbim_map: Dict[MatchKey, DividendRecord] = {}
    for record in nbim:
        nbim_map[record.key()] = record

    custodian_map: Dict[MatchKey, DividendRecord] = {}
    for record in custodian:
        custodian_map[record.key()] = record

    all_keys = set(nbim_map) | set(custodian_map)
    for key in sorted(all_keys, key=lambda k: (k.isin, k.account, k.pay_date)):
        result.add_pair(key, nbim_map.get(key), custodian_map.get(key))

    return result
