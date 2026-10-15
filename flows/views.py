
# from django.db.models import Prefetch
# from django.shortcuts import render

# from .models import Plan, Allowance


# def plans_list(request):
#     allowance_qs = (
#         Allowance.objects
#         .select_related("feature__category")
#         .order_by(
#             "feature__category__rank",
#             "feature__category__name",
#             "feature__name",
#         )
#     )

#     plans = (
#         Plan.objects
#         .filter(active=True)
#         .prefetch_related(
#             Prefetch("allowances", queryset=allowance_qs)
#         )
#     )

#     return render(request, "plans.html", {"plans": plans})