from django.db.models import Prefetch
from django.shortcuts import render

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






