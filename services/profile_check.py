from __future__ import annotations

from database import get_user


def is_profile_complete(user_id: int) -> bool:
    """Check if user has completed all 4 onboarding questions."""
    user = get_user(user_id)
    if user is None:
        return False
    name = user.get("full_name")
    children = user.get("has_children")  # 0 or 1
    workplace = user.get("workplace")
    city = user.get("city")
    return bool(name and children is not None and workplace and city)
