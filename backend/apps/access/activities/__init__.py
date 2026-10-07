"""The activities an owner can tag someone to prepare, in one place.

Each activity says who owns it (tags people and approves their requests), who may be tagged, what a
tag can be limited to, how a proposal is checked, how it reads in plain words and as before/after rows,
and how it is carried out. Carrying it out always calls the same function the owner's own screen uses,
run as the owner. Approving grades, staff accounts and access settings are never listed; the only
delete that can be proposed is a news post, and the Admin still approves it.
"""

from apps.access.activities.admin import (
    EditPrograms,
    EditWebsitePages,
    PostNews,
    RateProgramProfiles,
    ReviewRegistrations,
)
from apps.access.activities.base import (
    EXECUTION_ERRORS,
    ActivityFailed,
    my_access_path,
    tag_levels,
)
from apps.access.activities.head import PrepareAssignments, PreparePlacements, PrepareTermPlan, ReviewCorrections

ACTIVITIES = {
    activity.key: activity
    for activity in (
        ReviewRegistrations(),
        EditPrograms(),
        EditWebsitePages(),
        PostNews(),
        RateProgramProfiles(),
        PreparePlacements(),
        PrepareTermPlan(),
        PrepareAssignments(),
        ReviewCorrections(),
    )
}


def owned_by(role):
    return [activity for activity in ACTIVITIES.values() if activity.owner_role == role]


__all__ = ['ACTIVITIES', 'EXECUTION_ERRORS', 'ActivityFailed', 'my_access_path', 'owned_by', 'tag_levels']
