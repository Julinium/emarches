from bidding.models import Team, TeamMember


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
    memberships = user.memberships.all()
    last_membership = memberships.order_by("-joined").first()
    if last_membership:
        memberships.exclude(pk=last_membership.pk).delete()
        return last_membership.team
    else:
        try:
            name = 'TEAM-' + user.username
            team = Team.objects.create(
                creator = user,
                name=nam.strip().upper(),
            )
            team.add_member(user, True)
            return team
        except Exception as xc:
            pass

    return None


def get_colleagues(user=None):
    if not user: return None
    membership = user.memberships.order_by("joined").last()
    # membership = user.memberships.filter(active=True).last()
    return membership.team.members.filter(is_active=True).all() if membership else None


def update_membership(user=None, member=None, verb=None):
    if not user or not member or not verb: return None
    if user == member : return None
    try:
        memberships = member.memberships.all()
        last_membership = memberships.order_by("-joined").first()
        if last_membership:
            memberships.exclude(pk=last_membership.pk).delete()
            if verb:
                if verb == 'fire':
                    last_membership.delete()
                else:
                    if verb == 'disable':
                        last_membership.active = False
                    elif verb == 'enable':
                        last_membership.active = True
                    elif verb == 'bossify':
                        last_membership.manager = True
                    elif verb == 'debossify':
                        last_membership.manager = False
                    elif verb == 'debossify':
                        last_membership.manager = False
                    last_membership.save()
                return verb
        return None
    except: 
        return None
