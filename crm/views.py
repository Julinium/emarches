import logging
from urllib.parse import urlencode
from django.shortcuts import render
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import cache_control
from django.core.paginator import Paginator
from django.db.models import Case, CharField, Exists, F, OuterRef, Prefetch, Q, Subquery, Value, When
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from allauth.socialaccount.models import SocialAccount
from allauth.account.models import EmailAddress

from base.texter import normalize_text
from flows.models import Subscription, Cycle
from bidding.models import TeamMember

User = get_user_model()


ORDERING_FIELD = '-date_joined'
ITEMS_PER_PAGE = 25
logger_portal = logging.getLogger('portal')

@user_passes_test(lambda u: u.is_staff)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def customer_list_view(request):

    now = timezone.now()

    def get_req_params(req):
        allowed_keys = [
            'q', 'origin', 'staff', 'page', 'sort',
            'is_active', 'origin', 'joined', 'logged',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        
        if not 'sort' in query_dict:
            query_dict['sort'] = ORDERING_FIELD
        
        # dates_set = set(['ddlnn', 'ddlnx', 'publn', 'publx', 'delin', 'delix'])
        # if dates_set.isdisjoint(query_dict):
        #     query_dict['ddlnn'] = datetime.now(RABAT_TZ).strftime("%Y-%m-%d")

        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_customers(customers, params):
        
        def afas(queryset, field_names, phrase):
            phrase = normalize_text(phrase, False)
            words = [word.strip() for word in phrase.split() if word.strip()]
            if words:
                or_query = Q()
                for field in field_names:
                    field_q = Q()
                    for word in words:
                        field_q &= Q(**{f"{field}__icontains": word})
                    or_query |= field_q
                queryset = queryset.filter(or_query)

            return queryset
        ff = 0
        
        if not params: return customers.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            customers = afas(customers, [
                'username', 'email', 'first_name', 'last_name', 'profile__about', 
                'profile__phone', 'profile__whatsapp', 'memberships__team__name'
                ], q)
                
        if 'joined' in params:
            joined_filter = params.get('joined')
            if joined_filter:
                ff += 1
                
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if joined_filter == 'tday':
                    customers = customers.filter(date_joined__gte=today_start)
                elif joined_filter == 'yday':
                    yesterday_start = today_start - timedelta(days=1)
                    customers = customers.filter(date_joined__gte=yesterday_start, date_joined__lt=today_start)
                elif joined_filter == 'week':
                    # Assuming Monday is the start of the week
                    start_of_week = today_start - timedelta(days=today_start.weekday())
                    customers = customers.filter(date_joined__gte=start_of_week)
                elif joined_filter == 'lswk':
                    start_of_week = today_start - timedelta(days=today_start.weekday())
                    start_of_last_week = start_of_week - timedelta(days=7)
                    customers = customers.filter(date_joined__gte=start_of_last_week, date_joined__lt=start_of_week)
                elif joined_filter == 'mnth':
                    start_of_month = today_start.replace(day=1)
                    customers = customers.filter(date_joined__gte=start_of_month)
                elif joined_filter == 'lmth':
                    start_of_this_month = today_start.replace(day=1)
                    last_month_end = start_of_this_month
                    last_month_start = (start_of_this_month - timedelta(days=1)).replace(day=1)
                    customers = customers.filter(date_joined__gte=last_month_start, date_joined__lt=last_month_end)
                elif joined_filter == 'year':
                    start_of_year = today_start.replace(month=1, day=1)
                    customers = customers.filter(date_joined__gte=start_of_year)
                elif joined_filter == 'd365':
                    one_year_ago = now - timedelta(days=365)
                    customers = customers.filter(date_joined__gte=one_year_ago)

                
        if 'logged' in params:
            logged_filter = params.get('logged')
            if logged_filter:
                ff += 1
                
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if logged_filter == 'tday':
                    customers = customers.filter(last_login__gte=today_start)
                elif logged_filter == 'yday':
                    yesterday_start = today_start - timedelta(days=1)
                    customers = customers.filter(last_login__gte=yesterday_start, last_login__lt=today_start)
                elif logged_filter == 'week':
                    # Assuming Monday is the start of the week
                    start_of_week = today_start - timedelta(days=today_start.weekday())
                    customers = customers.filter(last_login__gte=start_of_week)
                elif logged_filter == 'lswk':
                    start_of_week = today_start - timedelta(days=today_start.weekday())
                    start_of_last_week = start_of_week - timedelta(days=7)
                    customers = customers.filter(last_login__gte=start_of_last_week, last_login__lt=start_of_week)
                elif logged_filter == 'mnth':
                    start_of_month = today_start.replace(day=1)
                    customers = customers.filter(last_login__gte=start_of_month)
                elif logged_filter == 'lmth':
                    start_of_this_month = today_start.replace(day=1)
                    last_month_end = start_of_this_month
                    last_month_start = (start_of_this_month - timedelta(days=1)).replace(day=1)
                    customers = customers.filter(last_login__gte=last_month_start, last_login__lt=last_month_end)
                elif logged_filter == 'year':
                    start_of_year = today_start.replace(month=1, day=1)
                    customers = customers.filter(last_login__gte=start_of_year)
                elif logged_filter == 'd365':
                    one_year_ago = now - timedelta(days=365)
                    customers = customers.filter(last_login__gte=one_year_ago)


        if 'origin' in params:
            origin_filter = params.get('origin')
            if origin_filter:
                ff += 1
                if origin_filter.lower() == 'direct':
                    customers = customers.filter(origin__isnull=True)
                else:
                    customers = customers.filter(origin=origin_filter)

        
        if 'is_active' in params:
            active_filter = params.get('is_active')
            if active_filter in ['true', 'false']:
                ff += 1
                customers = customers.filter(is_active=(active_filter == 'true'))
                filtered = True


        if 'staff' in params:
            staff_filter = params.get('staff')
            if staff_filter:
                ff += 1
                if staff_filter == 'superuser':
                    customers = customers.filter(is_superuser=True)
                    filtered = True
                elif staff_filter == 'staff':
                    customers = customers.filter(is_staff=True)
                    filtered = True
                elif staff_filter == 'regular':
                    customers = customers.filter(is_staff=False, is_superuser=False)
                    filtered = True

        if 'verified' in params:
            verified_filter = params.get('verified')
            if verified_filter in ['true', 'false']:
                ff += 1
                customers = customers.filter(is_verified=(verified_filter == 'true'))

        return customers.distinct(), ff

    def define_context(request):
        context = {}

        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        return context
  
    query_dict, query_string, query_unsorted = get_req_params(request)

    # active_cycles_prefetch = Prefetch(
    #     'cycles',
    #     queryset=Cycle.objects.filter(date_start__lte=now, date_end__gte=now),
    #     to_attr='active_cycles_list'
    # )
    # active_subscriptions_prefetch = Prefetch(
    #     'team__subscriptions',  # Default related name for Subscription.team ForeignKey
    #     queryset=Subscription.objects.filter(
    #         cycles__date_start__lte=now,
    #         cycles__date_end__gte=now
    #     ).select_related('plan').prefetch_related(active_cycles_prefetch),
    #     to_attr='active_subscriptions_list'
    # )
    # team_memberships_prefetch = Prefetch(
    #     'memberships',
    #     queryset=TeamMember.objects.select_related('team').prefetch_related(active_subscriptions_prefetch)
    # )

    verified_subquery = EmailAddress.objects.filter(user=OuterRef('pk'), verified=True, primary=True)
    social_subquery = SocialAccount.objects.filter(user=OuterRef('pk')).values('provider')[:1]

    active_cycles = Cycle.objects.filter(
        subscription__team__members=OuterRef('pk'),
        date_start__lte=now,
        date_end__gte=now
    )

    active_sub = Subscription.objects.filter(
        team__members=OuterRef('pk'),
        cycles__date_start__lte=now,
        cycles__date_end__gte=now
    ).select_related('plan').order_by('-created_at')
    
    status_subquery = active_sub.values('status')[:1]

    plan_subquery = active_sub.values('plan__translations__name')[:1]    

    all_customers = User.objects.annotate(
        social_provider=Subquery(social_subquery),
        origin=Case(
            When(social_provider__isnull=False, then='social_provider'),
            default=Value('organic'),
            output_field=CharField(),
        ),
        is_verified=Exists(verified_subquery),
        has_active_subscription=Exists(active_cycles),
        sub_status=Subquery(status_subquery),
        sub_plan=Subquery(plan_subquery),
    ).prefetch_related(
        # 'emailaddress_set',
        'memberships__team',
    ).select_related(
        'profile',
    )
    #############################
    fields = [
        'username', 'primary_email', 'first_name', 'last_name', 
        'origin', 'date_joined', 'last_login',
        'phone', 'whatsapp', 'about', 'avatar',
        'active_subscription', 'active_cycle', 
    ]
    #############################

   
    customers, filters = filter_customers(all_customers, query_dict)
    query_dict['filters'] = filters

    skey = query_dict.get('sort', '-j')

    ordering_map = {
        'u': 'username',
        '-u': '-username',
        '-j': 'date_joined',
        'j': '-date_joined',
        '-l': 'last_login',
        'l': '-last_login',
        # '-t': 'plan_tier',
        # 't': '-plan_tier',
        # '-r': 'cycle_end',
        # 'r': '-cycle_end',
    }
    case_insensitive_fields = ['username']

    sort = ordering_map.get(skey, ORDERING_FIELD)

    reverse = sort.startswith('-')
    field_name =sort.lstrip('-')
    ordering = Lower(field_name) if field_name in case_insensitive_fields else F(field_name)
    ordering = ordering.desc(nulls_last=True) if reverse else ordering.asc(nulls_last=True)
    customers = customers.order_by(ordering)

    context = define_context(request)

    paginator = Paginator(customers, ITEMS_PER_PAGE)
    page_number = query_dict['page'] if 'page' in query_dict else 1
    if '.' in str(page_number) or ',' in str(page_number): 
        page_number = page_number.replace(',', '').replace('.', '')
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    distinct_providers = SocialAccount.objects.values_list('provider', flat=True).distinct()
    origin_options = [{'value': 'organic', 'label': _('Organic')}]
    for provider in sorted(distinct_providers):
        origin_options.append({
            'value': provider, 
            'label': provider.replace('_', ' ').title() # e.g., 'linkedin_oauth2' -> 'Linkedin Oauth2'
        })

    context['page_obj']     = page_obj
    context['origin_options']     = origin_options

    logger_portal.info(f"Customers List view", extra={"request": request})


    return render(request, 'crm/customer_list.html', context)
    





