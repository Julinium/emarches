from django.db.models import Prefetch
# from django.shortcuts import render

from django.utils.translation import gettext as _

from .models import Category, Feature, Plan, Allowance


def get_plans():
    plans = list(
        Plan.objects.filter(active=True)
        .order_by("rank", "translations__name")
        .prefetch_related(
            Prefetch(
                "allowance_set",
                queryset=Allowance.objects.select_related("feature"),
                to_attr="loaded_allowances",
            )
        )
    )

    features = list(
        Feature.objects.filter(active=True)
        .select_related("category")
        .order_by("category__rank", "category__translations__name", "translations__name")
    )

    allowance_lookup = {}

    for plan in plans:
        for allowance in plan.loaded_allowances:
            allowance_lookup[(plan.pk, allowance.feature_id)] = (
                allowance.capability
            )

    feature_rows = []

    for feature in features:
        cells = []

        for plan in plans:
            capability = allowance_lookup.get(
                (plan.pk, feature.pk)
            )

            cells.append({
                "plan": plan,
                "capability": capability,
                "configured": (plan.pk, feature.pk) in allowance_lookup,
            })

        feature_rows.append({
            "feature": feature,
            "cells": cells,
        })

    category_groups = []

    for row in feature_rows:
        category = row["feature"].category

        if not category_groups or category_groups[-1]["category"] != category:
            category_groups.append({
                "category": category,
                "rows": [],
            })

        category_groups[-1]["rows"].append(row)

    return plans, category_groups


def planify():
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
    # return render(request, "plans/comparison.html", {
    #     "plans": plans,
    #     "rows": rows,
    # })





