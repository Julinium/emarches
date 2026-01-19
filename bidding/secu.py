from bidding.models import TeamMember


def is_team_admin(user, team):
    membership = TeamMember.objects.filter(
        user=user, team=team,
    ).first()

    if membership: return membership.patron == True

    return False