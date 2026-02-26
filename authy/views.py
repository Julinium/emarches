
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.cache import cache_control
# from django.contrib.auth.models import User
# from django.shortcuts import render


# @login_required(login_url="account_login")
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# def user_profile(request):
#     context = {}
#     user = request.user
#     user = (
#         request.user.__class__.objects
#         .select_related(
#             'profile',
#         # ).prefetch_related(
#             # 'newsletters',
#             # 'notifications',
#         )
#         .get(pk=request.user.pk)
#     )
#     context["user"] = user
#     return render(request, 'authy/user-profile.html', context)