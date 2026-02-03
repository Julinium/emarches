from bidding.models import TeamMember


def is_team_admin(user, team):
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