from django.contrib.auth import get_user_model

"""
NOTE(jason): This class extends the default Django user model with some additional
helper functions so that its interface matches the other TAS-compatible models
such as Projects and Allocations.

This isn't really the right way to do this, but adding a new User model at this
point is a bit of a bear.
"""


def patch_user_model():
    UserModel = get_user_model()
    UserModel.add_to_class("as_tas", _user_as_tas)


def _user_as_tas(user, role="Standard"):
    try:
        # Short-cut if we already know the user is a PI (because they are
        # marked as the PI for a project, for example.)
        if role == "PI":
            pi_eligibility = "Eligible"
        else:
            pi_eligibility = user.pi_eligibility()
    except Exception:
        pi_eligibility = "Ineligible"

    return {
        "username": user.username,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "source": "Chameleon",
        "email": user.email,
        "id": user.id,
        "piEligibility": pi_eligibility,
        "citizenship": None,
        "title": None,
        "phone": None,
        "country": None,
        "department": None,
        "institution": None,
        "role": role,
    }
