from bidding.models import TeamMember


def is_team_admin(user, team):
    membership = TeamMember.objects.filter(
        user=user, team=team,
    ).first()
    if membership: return membership.manager == True
    return False

def is_active_team_admin(user, team):
    membership = TeamMember.objects.filter(
        user=user, team=team, active=True,
    ).first()
    if membership: return membership.manager == True
    return False

def is_team_member(user, team):
    membership = TeamMember.objects.filter(
        user=user, team=team,
    ).first()
    if membership: return True
    return False

def is_active_team_member(user, team):
    membership = TeamMember.objects.filter(
        user=user, team=team, active=True,
    ).first()
    if membership: return True
    return False




def get_team(user=None):
    if not user: return None
    membership = user.memberships.last()
    return membership.team if membership else None

def get_colleagues(user=None):
    if not user: return None
    membership = user.memberships.last()
    return membership.team.members.all() if membership else None

def update_membership(user=None, member=None, verb=None):
    if not user or not member or not verb: return None
    if user == member : return None
    try:
        memberships = member.memberships.all()
        last_membership = memberships.order_by("joined").last()
        if last_membership:
            memberships.exclude(pk=last_membership.pk).delete()
            if verb:
                if verb == 'disable':
                    last_membership.active = False
                elif verb == 'enable':
                    last_membership.active = True
                elif verb == 'bossify':
                    last_membership.manager = True
                elif verb == 'debossify':
                    last_membership.manager = False
                last_membership.save()
                return verb
        return None
    except: 
        return None
