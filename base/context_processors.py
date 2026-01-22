
from nas.models import UserSetting, Favorite
from base.models import Category

def portal_context(request):

    context = {}
    
    bicons = {
        'filters'         : 'bi bi-front text-warning',
        'estimate'        : 'bi bi-cash-coin',
        'bond'            : 'bi bi-safe',    
                            # bookmark-check
                            # piggy-bank 
                            # credit-card
        'published'       : 'bi bi-clock',
        'multi_lots'      : 'bi bi-ui-radios-grid',  
                            # 'grid'
                            # 'ui-checks-grid'
        'category'        : 'bi bi-grid',
        'location'        : 'bi bi-pin-map',
                            # 'geo'
        'client'          : 'bi bi-briefcase',
                            # 'house-door'         # 'bank'
        'deadline'        : 'bi bi-hourglass',
                            # 'calendar4-event' -bottom
        'reference'       : 'bi bi-tag',
        'restricted'      : 'bi bi-intersect text-danger',       
                            # 'bell-slash-fill text-danger'
        'reserved_ico'    : 'bi bi-sign-yield',
        'variant_ico'     : 'bi bi-shuffle',
        'reserved'        : 'bi bi-sign-yield-fill text-primary',
        'variant'         : 'bi bi-shuffle text-success',
        'count'           : 'bi bi-grid-3x3-gap',
                            # '123' 

        'has_agrements'   : 'bi bi-shield-fill-check text-primary',
        'has_qualifs'     : 'bi bi-mortarboard-fill text-primary',
        'has_samples'     : 'bi bi-palette2 text-primary',
        'has_visits'      : 'bi bi-person-walking text-primary',
                            # 'eye-fill'
        'has_meetings'    : 'bi bi-chevron-bar-contract text-primary',

        'agrements_ico'   : 'bi bi-shield-check',
        'qualifs_ico'     : 'bi bi-mortarboard',
        'samples_ico'     : 'bi bi-palette2',
        'visits_ico'      : 'bi bi-person-walking',
        'meetings_ico'    : 'bi bi-chevron-bar-contract',
        
        'changes'         : 'bi bi-activity',
                            # 'pencil-square'
        'favorites'       : 'bi bi-heart',
        'downloads'       : 'bi bi-arrow-down-square',
        'views'           : 'bi bi-eye', 
                            # 'bi bi-compass',
        'favorite'        : 'bi bi-heart',
        'favorited'       : 'bi bi-heart-fill',
        'unfavorite'      : 'bi bi-heartbreak',
        'comments'        : 'bi bi-chat-square-quote',
        'ebid'            : 'bi bi-laptop',
        'ebid_req'        : 'bi bi-laptop text-primary',
        'ebid_opt'        : 'bi bi-laptop text-success',
        'ebid_na'         : 'bi bi-laptop text-danger',
                            # 'pc-display-horizontal'
        'esign'           : 'bi bi-usb-drive', 
        'esign_req'       : 'bi bi-usb-drive text-primary', 
        'esign_opt'       : 'bi bi-usb-drive text-success', 
        'esign_na'        : 'bi bi-usb-drive text-secondary',       
                            # 'device-ssd'
        'link'            : 'bi bi-box-arrow-up-right',
        'bidding'         : 'bi bi-envelope-arrow-up',
                            # arrow-90deg-right
                            # send-check
                            # reply 
                            # handbag 
                            # arrow-up-right-square 
                            # check-square
                            # 
                            # box-arrow-in-up
                            # box-arrow-in-up-right
        'search'          : 'bi bi-search',
        'sort'            : 'bi bi-arrow-down-up',
        'sort_up'         : 'bi bi-arrow-up',
        'sort_down'       : 'bi bi-arrow-down',
        'backspace'       : 'bi bi-backspace',
        'filter'          : 'bi bi-funnel',
                            # binoculars
        'days_to_go'      : 'bi bi-stopwatch',
                            # calendar-x
        'title'           : 'bi bi-card-heading',
        'procedure'       : 'bi bi-book',
        'mode'            : 'bi bi-filter-left',
        'domains'         : 'bi bi-layers',
        'address'         : 'bi bi-geo-alt',
        'contact'         : 'bi bi-person',
        'no_files'        : 'bi bi-file-earmark-break text-warning',
        'files_size'      : 'bi bi-folder2',
                            # exclamation-circle
        'share'           : 'bi bi-share',
        'created'         : 'bi bi-calendar-plus',
                            # upload
        'updated'         : 'bi bi-arrow-repeat',
        'database'        : 'bi bi-database',
        'hash'            : 'bi bi-hash',
        'days_span'       : 'bi bi-calendar-range',
                            # arrows-expand-vertical
        'history'         : 'bi bi-clock-history',
                            # 
        'delete'          : 'bi bi-trash',
        'clean_expired'   : 'bi bi-hourglass-bottom',
        'clean_cancelled' : 'bi bi-x-octagon',
        'clean_all'       : 'bi bi-heart',
        'insights'        : 'bi bi-bar-chart-line',
        'shopping'        : 'bi bi-cart4',
        'simulator'       : 'bi bi-dpad',

        'tenders'         : 'bi bi-rocket-takeoff', 
                            # megaphone 
                            # radioactive
                            # shop-window
        'bdc'             : 'bi bi-basket',
                            # bar-chart-steps
                            # controller
        'plus'            : 'bi bi-plus-lg',
        'winner'          : 'bi bi-trophy-fill',
        'range'           : 'bi bi-arrows',
                            # arrows-expand-vertical
                            # arrow-left-right
        'range_min'       : 'bi bi-arrow-bar-up',
        'range_max'       : 'bi bi-arrow-bar-down',
        'target'          : 'bi bi-crosshair',
                            # bullseye

        'mean'            : 'bi bi-arrows-collapse',
        'close'           : 'bi bi-x-lg',
        'ratio'           : 'bi bi-percent',
        'send'            : 'bi bi-send',
        'support'         : 'bi bi-headset',

        'specs'           : 'bi bi-card-list',
        'warranties'      : 'bi bi-exclamation-diamond',
        'deliberated'     : 'bi bi-check-square',
        'articles'        : 'bi bi-list-check',
        'settings'        : 'bi bi-sliders2',

        'pinned'          : 'bi bi-heart-fill',
        'unpinned'        : 'bi bi-heartbreak',

        'expired'         : 'bi bi-hourglass-bottom',
        'nature'          : 'bi bi-tags',

        'unsuccessful'    : 'bi bi-hand-thumbs-down-fill',
        'ongoing'         : 'bi bi-hourglass-top', 
                            # calendar2-check

        'concurrence'     : 'bi bi-bar-chart-steps',
                            # filter-left 
                            # sort-up 
                            # list-ol 
                            
        'company'         : 'bi bi-buildings',
                            
        'bid'             : 'bi bi-envelope-arrow-up',
        'bid_fill'        : 'bi bi-envelope-arrow-up-fill text-primary',

        'vertical'        : 'bi bi-three-dots-vertical',
        'details'         : 'bi bi-card-text',
        'edit'            : 'bi bi-pencil',
        'goto'            : 'bi bi-cursor',
        'download'        : 'bi bi-download',
        'section'         : 'bi bi-play',

        'team'            : 'bi bi-diagram-3',
        'task'            : 'bi bi-journal-check',
        'contract'        : 'bi bi-bag-check',
        'expense'         : 'bi bi-credit-card',
        'payment'         : 'bi bi-piggy-bank',
        'reception'       : 'bi bi-check2-square',

        'duplicate'       : 'bi bi-layers-fill',
        'status'          : 'bi bi-bar-chart',
        'analysis'        : 'bi bi-cpu',

    }

    context['bicons']        = bicons
    # context['empty_items']   = ['-', '--', '_', '__', '---', '/', '?', ' ', '.', '']

    context['categories'] = Category.objects.all().order_by('label')

    user = request.user
    if not user or not user.is_authenticated:
        return context        

    user_settings = UserSetting.objects.filter(user = request.user).first()
    if not user_settings: user_settings = UserSetting.objects.create(user=request.user)

    faved_ids  = user.favorites.values_list('tender', flat=True)
    pinned_ids = user.stickies.values_list('purchase_order', flat=True)

    # TODO: Permission logic
    show_bidders_names = False
    user = request.user
    if user and user.is_superuser:
        show_bidders_names = True


    context['user_settings'] = user_settings
    context['faved_ids']     = faved_ids
    context['pinned_ids']    = pinned_ids
    context['wrap_text']     = user_settings.general_wrap_long_text == True
    context['show_bidders_names']     = show_bidders_names

    return context



