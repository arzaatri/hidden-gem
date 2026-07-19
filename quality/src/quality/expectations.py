"""Defines the Great Expectations suite validating the raw IGDB bronze pull.

These are structural sanity bounds (rating ranges, non-negative counts,
plausible timestamps), not user-tunable knobs — so there's no config.yaml
entry; adjust here directly if IGDB's data shape changes. Bounds on
non-required columns pass `None` values through untested by default (GE's
column-map expectations only evaluate present values), matching the
"nulls pass" convention already used for `recommendation.rating_cutoff`.
"""

from __future__ import annotations

import time

import great_expectations as gx

SUITE_NAME = "bronze_games_suite"

_ONE_DAY_SECONDS = 24 * 60 * 60
_FIVE_YEARS_SECONDS = 5 * 365 * _ONE_DAY_SECONDS
_NOW_EPOCH_FLOOR = 946_684_800  # 2000-01-01T00:00:00Z — sane floor for `updated_at` (an IGDB edit timestamp)
_EARLIEST_GAME_EPOCH = -631_152_000  # 1950-01-01T00:00:00Z — comfortably before any real video game


def build_bronze_suite() -> gx.ExpectationSuite:
    """Requires an active Great Expectations context (call gx.get_context() first)."""
    now = int(time.time())

    suite = gx.ExpectationSuite(name=SUITE_NAME)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="name"))
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="rating", min_value=0, max_value=100)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="aggregated_rating", min_value=0, max_value=100
        )
    )
    for column in ("aggregated_rating_count", "follows", "hypes"):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column=column, min_value=0))

    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="updated_at"))
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="updated_at", min_value=_NOW_EPOCH_FLOOR, max_value=now + _ONE_DAY_SECONDS
        )
    )
    # first_release_date spans real retro games (pre-2000) through legitimately
    # future-dated announced/upcoming titles, so its bounds are much wider than
    # updated_at's (an IGDB edit timestamp, which is never historical).
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="first_release_date",
            min_value=_EARLIEST_GAME_EPOCH,
            max_value=now + _FIVE_YEARS_SECONDS,
        )
    )
    return suite
