from django.db.models import Prefetch

from django.utils.translation import gettext as _

from .models import Category, Feature, Plan, Allowance


def comparify():
    """
    """
    plans = list(
        Plan.objects.filter(active=True)
        .order_by("rank")
        .prefetch_related(
            Prefetch(
                "allowance_set",
                queryset=Allowance.objects.select_related("feature"),
            )
        )
    )

    categories = list(
        Category.objects.filter(active=True)
        .order_by("rank")
        .prefetch_related(
            Prefetch(
                "features",
                queryset=Feature.objects.filter(active=True).order_by("rank"),
            )
        )
    )

    # Build one allowance lookup per plan.
    allowances_by_plan = {
        plan.pk: {
            allowance.feature_id: allowance.capability
            for allowance in plan.allowance_set.all()
        }
        for plan in plans
    }

    rows = []

    for category in categories:
        features = list(category.features.all())

        if not features:
            continue

        category_rows = []

        for feature in features:
            cells = []

            for plan in plans:
                capability = allowances_by_plan[plan.pk].get(
                    feature.pk, 0
                )

                cells.append({
                    "is_binary": feature.is_binary,
                    "enabled": bool(capability),
                    "capability": capability,
                })

            category_rows.append({
                "feature": feature,
                "cells": cells,
            })

        rows.append({
            "category": category,
            "features": category_rows,
        })

    # Include active features that have no category.
    uncategorized = Feature.objects.filter(
        active=True,
        category__isnull=True,
    ).order_by("rank")

    uncategorized_rows = []

    for feature in uncategorized:
        cells = []

        for plan in plans:
            capability = allowances_by_plan[plan.pk].get(feature.pk, 0)

            cells.append({
                "is_binary": feature.is_binary,
                "enabled": bool(capability),
                "capability": capability,
            })

        uncategorized_rows.append({
            "feature": feature,
            "cells": cells,
        })

    if uncategorized_rows:
        rows.append({
            "category": None,
            "features": uncategorized_rows,
        })
    
    return plans, rows


def planify():
    plans = list(
        Plan.objects
        .filter(active=True)
        .order_by("rank", "code")
        .prefetch_related(
            "translations",
            "allowance_set__feature__translations",
        )
    )

    effective = {}
    previous_plan_name = None

    for plan in plans:
        previous = effective.copy()

        # Apply this plan's explicit allowances to inherited entitlements.
        for allowance in plan.allowance_set.all():
            effective[allowance.feature_id] = allowance

        # Display only new or changed entitlements.
        plan.new_allowances = [
            allowance
            for feature_id, allowance in effective.items()
            if (
                feature_id not in previous
                or allowance.capability
                != previous[feature_id].capability
            )
        ]

        plan.inherited_plan_name = previous_plan_name
        plan.has_inherited_features = previous_plan_name is not None

        # Store the cumulative state for the next plan.
        plan.effective_allowances = sorted(
            effective.values(),
            key=lambda a: (a.feature.rank, a.feature.code),
        )

        previous_plan_name = plan.name
    return plans


def summarify():
    
    return {}
