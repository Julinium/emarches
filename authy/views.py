
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render


@login_required
def user_profile(request):
    context = {}
    user = request.user
    user = (
        request.user.__class__.objects
        .select_related(
            'profile',
        ).prefetch_related(# 'groups', # 'user_permissions',
            'companies',            # Company
            # 'folders',              # Folder
            # 'favorites',            # Fovorite
            # 'downloads',            # Download
            # 'letters',              # Letter
            'newsletters',          # NewsletterSubscription
            'notifications',        # NotificationSubscription
            # 'sent_letters',         # LetterSent
            # 'sent_notifications',   # NotificationSent
            # 'comments',             # Comment
            # 'reactions',            # Reaction
            # 'settings',             # UserSetting

            ## ---- nested / filtered prefetch ----
            ## Prefetch(
            ##     'posts',
            ##     queryset=Post.objects.select_related('category')
            ##                         .filter(is_published=True)
            ##                         .order_by('-created_at'),
            ##     to_attr='published_posts'   # optional custom attribute
            ## ),
        )
        .get(pk=request.user.pk)
    )
    context["user"] = user
    return render(request, 'authy/user-profile.html', context)