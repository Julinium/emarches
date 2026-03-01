import logging

from datetime import datetime, timedelta
from django.utils.translation import gettext_lazy as _

from bidding.models import Team, TeamMember

logger_portal = logging.getLogger("portal")


def get_or_create_team(user=None, request=None):
    if not user: return None
    memberships = user.memberships.all()
    last_membership = memberships.order_by("-joined").first()
    if last_membership:
        try:
            back48h = datetime.now() - timedelta(hours=60)
            canvs = user.invitations.filter(cancelled=True) | user.invitations.filter(expiry__lt=back48h)
            dc, dd = canvs.delete()
            logger_portal.debug(f"Deleted { dc } dead Invitations: { dd }", extra={"request": request})
        except:
            logger_portal.exception("Exception deleting dead Invitations", extra={"request": request})
        try:
            others = memberships.exclude(pk=last_membership.pk)
            dc, dd = others.delete()
            logger_portal.debug(f"Deleted { dc } Memebeships: { dd }", extra={"request": request})
        except:
            logger_portal.exception("Exception handling other Memberships", extra={"request": request})

        return last_membership.team
        
    else:
        emp_teams = user.teams.filter(members__isnull=True)
        try:
            dc, dd = emp_teams.delete()
            logger_portal.debug(f"Deleted { dc } empty Teams: { dd }", extra={"request": request})
        except:
            logger_portal.exception("Exception handling empty Teams", extra={"request": request})
            
        try:
            team = Team.objects.create(  
                name= f"TEAM-{ user.username.upper() }",
                creator=user,
            )
            logger_portal.debug(f"Team created { team.name }", extra={"request": request})

            team.add_member(user, manager=True)
            logger_portal.debug(f"User { user.id } added to team { team.name }", extra={"request": request})
            return team
        except Exception as xc:
            logger_portal.exception(f"Exception creating Team and membership: { xc }", extra={"request": request})

    return None


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

def get_colleagues(user=None):
    if not user: return None
    membership = user.memberships.order_by("joined").last()
    return membership.team.members.filter(is_active=True).all() if membership else None


def update_membership(user=None, member=None, verb=None, request=None):
    if not user or not member or not verb: 
        logger_portal.debug("update_membership failed: Bad parameters", extra={"request": request})
        return None
    if user == member : 
        logger_portal.debug("update_membership failed: Self editing", extra={"request": request})
        return None
    try:
        memberships = member.memberships.all()
        last_membership = memberships.order_by("-joined").first()
        if last_membership:
            try:
                others = memberships.exclude(pk=last_membership.pk)
                dc, dd = others.delete()
                logger_portal.debug(f"Deleted { dc } Memebeships: { dd }", extra={"request": request})
            except:
                logger_portal.exception("Exception handling other Memberships", extra={"request": request})
            
            if verb == 'fire':
                last_membership.delete()
                logger_portal.info("Deleted membership successfully", extra={"request": request})
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
                logger_portal.info(f"Updated membership with: { verb }", extra={"request": request})
            return verb
        
        logger_portal.warning("No last membership not found", extra={"request": request})
        return None
    except: 
        logger_portal.exception("Exception updating membership", extra={"request": request})
        return None


# def hire(user=None, team=None):
#     if is_team_member(user, team): return True

