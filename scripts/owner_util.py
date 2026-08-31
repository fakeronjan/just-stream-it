"""This league's own owner-identity helpers - NOT stable across the ESPN
platform (unlike espn_maps.py), specific to Just Stream It's actual people.

Shared by build_keeper_guide.py and build_weekly_recap.py; previously
duplicated between them, which is exactly how they'd drift out of sync if
a nickname ever changed in one place and not the other.
"""

# A couple of owners go by a nickname in league chatter/spreadsheets that
# isn't their ESPN account's first name.
OWNER_NICKNAMES = {
    "Michael Higgins": "Mike",
    "Joseph Sebranek": "Joe",
    "Karlos Abel": "Karl",
}


def owner_first_name(owners):
    full = owners[0] if owners else ""
    return OWNER_NICKNAMES.get(full, full.split()[0])
