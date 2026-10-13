"""
Reusable Lead Conversion Prediction Target Builder.

This module is CRM-independent.

The CRM adapter is responsible for determining the
appropriate business outcome. This module only converts
that standardized outcome into the model target.
"""


TARGET_FIELD = "converted"


def build_conversion_target(outcome_records):
    """
    Build the standardized conversion target.

    Parameters
    ----------
    outcome_records : list[dict]
        Records containing a universal conversion outcome.

        Expected field:
            converted

        The value must represent a defensible business
        conversion outcome determined by the CRM adapter.

    Returns
    -------
    list[int]
        Binary conversion targets.
    """

    targets = []

    for record in outcome_records:

        converted = record.get(TARGET_FIELD)

        if converted is None:
            raise ValueError(
                "Missing 'converted' target in outcome record."
            )

        targets.append(
            1 if bool(converted) else 0
        )

    return targets
