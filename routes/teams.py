"""
Unified Sports Registration and Team Management routes for Inter-Dept Sports Meet.
Stores department teams inside the 'departments' database, where each department
(e.g., amsc, pe, ppe) has its own collection, containing each sport being played,
and each sport field contains the team that has been registered.
Teams are identified directly by Department and Sport without team names.
"""

import os
import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database.config import get_client
from routes.auth import ALLOWED_DEPARTMENTS, extract_department

router = APIRouter(tags=["Registration & Teams"])
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Sports Specification and Limits (16 sports - strictly following tournament plan)
SPORTS_CONFIG: dict[str, dict[str, Any]] = {
    "cricket_boys": {
        "id": "cricket_boys",
        "name": "Cricket (boys)",
        "category": "Boys",
        "icon": "🏏",
        "main_count": 11,
        "sub_max": 4,
        "formula": "11 + 4",
        "squad_notation": "11 Playing (1 Captain + 10 Main) + up to 4 Substitutes (Bench)",
        "squad_badge": "11 Playing + up to 4 Subs",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 11 to 15 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "11 Playing Players (1 Captain + 10 Main) + up to 4 Substitutes on bench. Total squad: 11 to 15 Boys.",
        "default_gender": "Boy",
    },
    "box_cricket_girls": {
        "id": "box_cricket_girls",
        "name": "Box cricket (girls)",
        "category": "Girls",
        "icon": "🏏",
        "main_count": 5,
        "sub_max": 3,
        "formula": "5 + 3",
        "squad_notation": "5 Playing (1 Captain + 4 Main) + up to 3 Substitutes (Bench)",
        "squad_badge": "5 Playing + up to 3 Subs",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 5 to 8 squad members (Captain, Main squad, and Bench) must be female students ('Girl').",
        "description": "5 Playing Players (1 Captain + 4 Main) + up to 3 Substitutes on bench. Total squad: 5 to 8 Girls.",
        "default_gender": "Girl",
    },
    "football_boys": {
        "id": "football_boys",
        "name": "Football (boys)",
        "category": "Boys",
        "icon": "⚽",
        "main_count": 7,
        "sub_max": 3,
        "formula": "7 + 3",
        "squad_notation": "7 Playing (1 Captain + 6 Main) + up to 3 Substitutes (Bench)",
        "squad_badge": "7 Playing + up to 3 Subs",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 7 to 10 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "7 Playing Players (1 Captain + 6 Main) + up to 3 Substitutes on bench. Total squad: 7 to 10 Boys.",
        "default_gender": "Boy",
    },
    "football_girls": {
        "id": "football_girls",
        "name": "Football (girls)",
        "category": "Girls",
        "icon": "⚽",
        "main_count": 3,
        "sub_max": 2,
        "formula": "3 + 2",
        "squad_notation": "3 Playing (1 Captain + 2 Main) + up to 2 Substitutes (Bench)",
        "squad_badge": "3 Playing + up to 2 Subs",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 3 to 5 squad members (Captain, Main squad, and Bench) must be female students ('Girl').",
        "description": "3 Playing Players (1 Captain + 2 Main) + up to 2 Substitutes on bench. Total squad: 3 to 5 Girls.",
        "default_gender": "Girl",
    },
    "volleyball_boys": {
        "id": "volleyball_boys",
        "name": "Volleyball (boys)",
        "category": "Boys",
        "icon": "🏐",
        "main_count": 6,
        "sub_max": 2,
        "formula": "6 + 2",
        "squad_notation": "6 Playing (1 Captain + 5 Main) + up to 2 Substitutes (Bench)",
        "squad_badge": "6 Playing + up to 2 Subs",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 6 to 8 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "6 Playing Players (1 Captain + 5 Main) + up to 2 Substitutes on bench. Total squad: 6 to 8 Boys.",
        "default_gender": "Boy",
    },
    "badminton_mix": {
        "id": "badminton_mix",
        "name": "Badminton (mix)",
        "category": "Mixed",
        "icon": "🏸",
        "main_count": 4,
        "sub_max": 2,
        "formula": "b2,g2 + up to 2 (max 1B, 1G)",
        "squad_notation": "4 Playing (1 Captain + 3 Main: exactly 2 Boys & 2 Girls) + up to 2 Substitutes (at most 1 Boy & 1 Girl)",
        "squad_badge": "4 Playing (2B + 2G) + up to 2 Subs",
        "gender_badge": "👫 Mixed: 2 Boys & 2 Girls Playing (Subs: max 1B, 1G)",
        "gender_rule_desc": "The 4 playing squad members (Captain + Main squad) MUST include exactly 2 Boys and 2 Girls. Up to 2 substitutes are allowed (at most 1 Boy and at most 1 Girl).",
        "description": "4 Playing Players (1 Captain + 3 Main: exactly 2 Boys and 2 Girls) + up to 2 Substitutes on bench (at most 1 Boy and at most 1 Girl). Total squad: 4 to 6 Athletes.",
        "gender_spec": "2 Boys & 2 Girls Playing (Subs: max 1B, 1G)",
        "default_gender": "Boy",
    },
    "tt_boys": {
        "id": "tt_boys",
        "name": "TT (boys)",
        "category": "Boys",
        "icon": "🏓",
        "main_count": 3,
        "sub_max": 2,
        "formula": "3 + 2",
        "squad_notation": "3 Playing (1 Captain + 2 Main) + up to 2 Substitutes (Bench)",
        "squad_badge": "3 Playing + up to 2 Subs",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 3 to 5 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "3 Playing Players (1 Captain + 2 Main) + up to 2 Substitutes on bench. Total squad: 3 to 5 Boys.",
        "default_gender": "Boy",
    },
    "carrom_mix": {
        "id": "carrom_mix",
        "name": "Carrom (mix)",
        "category": "Mixed",
        "icon": "🎯",
        "main_count": 2,
        "sub_max": 2,
        "formula": "b1,g1 + up to 2 (max 1B, 1G)",
        "squad_notation": "2 Playing (1 Captain + 1 Main: exactly 1 Boy & 1 Girl) + up to 2 Substitutes (at most 1 Boy & 1 Girl)",
        "squad_badge": "2 Playing (1B + 1G) + up to 2 Subs",
        "gender_badge": "👫 Mixed: 1 Boy & 1 Girl Playing (Subs: max 1B, 1G)",
        "gender_rule_desc": "The 2 playing squad members (Captain + 1 Main player) MUST include exactly 1 Boy and 1 Girl. Up to 2 substitutes are allowed (at most 1 Boy and at most 1 Girl).",
        "description": "2 Playing Players (1 Captain + 1 Main: exactly 1 Boy and 1 Girl) + up to 2 Substitutes on bench (at most 1 Boy and at most 1 Girl). Total squad: 2 to 4 Athletes.",
        "gender_spec": "1 Boy & 1 Girl Playing (Subs: max 1B, 1G)",
        "default_gender": "Boy",
    },
    "tow_boys": {
        "id": "tow_boys",
        "name": "TOW (boys)",
        "category": "Boys",
        "icon": "🪢",
        "main_count": 7,
        "sub_max": 2,
        "formula": "7 + 2",
        "squad_notation": "7 Playing (1 Captain + 6 Main) + up to 2 Substitutes (Bench)",
        "squad_badge": "7 Playing + up to 2 Subs",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 7 to 9 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "7 Playing Players (1 Captain + 6 Main) + up to 2 Substitutes on bench. Total squad: 7 to 9 Boys.",
        "default_gender": "Boy",
    },
    "tow_girls": {
        "id": "tow_girls",
        "name": "TOW (girls)",
        "category": "Girls",
        "icon": "🪢",
        "main_count": 5,
        "sub_max": 2,
        "formula": "5 + 2",
        "squad_notation": "5 Playing (1 Captain + 4 Main) + up to 2 Substitutes (Bench)",
        "squad_badge": "5 Playing + up to 2 Subs",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 5 to 7 squad members (Captain, Main squad, and Bench) must be female students ('Girl').",
        "description": "5 Playing Players (1 Captain + 4 Main) + up to 2 Substitutes on bench. Total squad: 5 to 7 Girls.",
        "default_gender": "Girl",
    },
    "shotput_boys": {
        "id": "shotput_boys",
        "name": "Shotput (boys)",
        "category": "Boys",
        "icon": "☄️",
        "main_count": 2,
        "sub_max": 1,
        "formula": "2 + 1",
        "squad_notation": "2 Playing (1 Captain + 1 Main) + up to 1 Substitute (Bench)",
        "squad_badge": "2 Playing + up to 1 Sub",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 2 to 3 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "2 Playing Players (1 Captain + 1 Main) + up to 1 Substitute on bench. Total squad: 2 to 3 Boys.",
        "default_gender": "Boy",
    },
    "shotput_girls": {
        "id": "shotput_girls",
        "name": "Shotput (girls)",
        "category": "Girls",
        "icon": "☄️",
        "main_count": 1,
        "sub_max": 1,
        "formula": "1 + 1",
        "squad_notation": "1 Playing (Captain) + up to 1 Substitute (Bench)",
        "squad_badge": "1 Playing + up to 1 Sub",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 1 to 2 squad members (Captain and Bench) must be female students ('Girl').",
        "description": "1 Playing Player (Captain) + up to 1 Substitute on bench. Total squad: 1 to 2 Girls.",
        "default_gender": "Girl",
    },
    "discus_boys": {
        "id": "discus_boys",
        "name": "Discus throw (boys)",
        "category": "Boys",
        "icon": "🥏",
        "main_count": 2,
        "sub_max": 1,
        "formula": "2 + 1",
        "squad_notation": "2 Playing (1 Captain + 1 Main) + up to 1 Substitute (Bench)",
        "squad_badge": "2 Playing + up to 1 Sub",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 2 to 3 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "2 Playing Players (1 Captain + 1 Main) + up to 1 Substitute on bench. Total squad: 2 to 3 Boys.",
        "default_gender": "Boy",
    },
    "discus_girls": {
        "id": "discus_girls",
        "name": "Discus throw (girls)",
        "category": "Girls",
        "icon": "🥏",
        "main_count": 1,
        "sub_max": 1,
        "formula": "1 + 1",
        "squad_notation": "1 Playing (Captain) + up to 1 Substitute (Bench)",
        "squad_badge": "1 Playing + up to 1 Sub",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 1 to 2 squad members (Captain and Bench) must be female students ('Girl').",
        "description": "1 Playing Player (Captain) + up to 1 Substitute on bench. Total squad: 1 to 2 Girls.",
        "default_gender": "Girl",
    },
    "long_jump_boys": {
        "id": "long_jump_boys",
        "name": "Long jump (boys)",
        "category": "Boys",
        "icon": "🏃‍♂️",
        "main_count": 2,
        "sub_max": 1,
        "formula": "2 + 1",
        "squad_notation": "2 Playing (1 Captain + 1 Main) + up to 1 Substitute (Bench)",
        "squad_badge": "2 Playing + up to 1 Sub",
        "gender_badge": "👦 Strictly Boys Only",
        "gender_rule_desc": "All 2 to 3 squad members (Captain, Main squad, and Bench) must be male students ('Boy').",
        "description": "2 Playing Players (1 Captain + 1 Main) + up to 1 Substitute on bench. Total squad: 2 to 3 Boys.",
        "default_gender": "Boy",
    },
    "long_jump_girls": {
        "id": "long_jump_girls",
        "name": "Long jump (girls)",
        "category": "Girls",
        "icon": "🏃‍♀️",
        "main_count": 1,
        "sub_max": 1,
        "formula": "1 + 1",
        "squad_notation": "1 Playing (Captain) + up to 1 Substitute (Bench)",
        "squad_badge": "1 Playing + up to 1 Sub",
        "gender_badge": "👧 Strictly Girls Only",
        "gender_rule_desc": "All 1 to 2 squad members (Captain and Bench) must be female students ('Girl').",
        "description": "1 Playing Player (Captain) + up to 1 Substitute on bench. Total squad: 1 to 2 Girls.",
        "default_gender": "Girl",
    },
}

MESSAGES: dict[str, str] = {
    "team_created": "🎉 Registration submitted successfully! Your department team roster is saved.",
    "team_updated": "✅ Team roster updated successfully.",
    "team_deleted": "🗑️ Team removed successfully.",
}

ERRORS: dict[str, str] = {
    "user_already_has_team": "⚠️ You have already formed a team for this sport. Each student can form at most 1 team of their own per sport. You can edit or delete your existing team.",
    "duplicate_roster": "⚠️ Team already exists! An identical squad roster has already been registered for this sport.",
    "already_registered": "⚠️ A team with this exact roster already exists.",
    "missing_captain": "⚠️ Captain details (Name, IITR Email, Student ID) are required.",
    "missing_main_player": "⚠️ All required main squad players must have their Name, IITR Email, and Student ID entered.",
    "cross_dept_player": "⚠️ All team players must belong to your own department. Players from other departments cannot be added.",
    "duplicate_player_in_team": "⚠️ Duplicate player detected within the team! The same student cannot be added multiple times in the same squad.",
    "gender_rule_boys": "⚠️ Strict Gender Rule: Only male athletes ('Boy') can be registered for this sport.",
    "gender_rule_girls": "⚠️ Strict Gender Rule: Only female athletes ('Girl') can be registered for this sport.",
    "gender_rule_badminton": "⚠️ Mixed Event Rule: Badminton (mix) playing squad must contain exactly 2 Boys and 2 Girls (Substitutes: at most 1 Boy and 1 Girl).",
    "gender_rule_carrom": "⚠️ Mixed Event Rule: Carrom (mix) playing squad must contain exactly 1 Boy and 1 Girl (Substitutes: at most 1 Boy and 1 Girl).",
    "no_subs_allowed": "⚠️ Substitutes are not permitted for this sport.",
    "unauthorized": "You are only permitted to edit or delete registrations created by yourself.",
    "db_error": "Database operation failed. Please check network connection.",
    "invalid_sport": "Selected sport is invalid.",
    "team_not_found": "Specified team was not found.",
}


def _get_current_user(request: Request) -> dict[str, Any] | None:
    return request.session.get("user")


def _get_user_dept(user: dict[str, Any]) -> str:
    """
    Extracts and normalizes the student's department code.
    Strictly locks each student to their own department.
    """
    return (user.get("department") or "").strip().lower()


def _get_dept_collection(dept: str):
    """
    Returns the AsyncMongoCollection from the 'departments' database.
    """
    client = get_client()
    return client["departments"][dept.lower()]


def are_members_same(m1: dict[str, Any], m2: dict[str, Any]) -> bool:
    """Check if two player records refer to the same student."""
    e1 = (m1.get("email") or "").strip().lower()
    e2 = (m2.get("email") or "").strip().lower()
    if e1 and e2:
        return e1 == e2

    id1 = (m1.get("student_id") or "").strip().lower()
    id2 = (m2.get("student_id") or "").strip().lower()
    if id1 and id2:
        return id1 == id2

    n1 = " ".join((m1.get("name") or "").strip().lower().split())
    n2 = " ".join((m2.get("name") or "").strip().lower().split())
    return bool(n1 and n1 == n2)


def get_all_team_members(team: dict[str, Any]) -> list[dict[str, Any]]:
    """Collects all members (captain + main players + substitutes) from a team dictionary."""
    members = []
    captain = team.get("captain")
    if isinstance(captain, dict) and captain.get("name"):
        members.append(captain)
    for p in team.get("main_players") or []:
        if isinstance(p, dict) and p.get("name"):
            members.append(p)
    for s in team.get("substitutes") or []:
        if isinstance(s, dict) and s.get("name"):
            members.append(s)
    return members


def are_team_rosters_identical(team_a: dict[str, Any], team_b: dict[str, Any]) -> bool:
    """
    Returns True if none of the members are different between team_a and team_b.
    Every member in team_a must match a member in team_b, and vice versa.
    """
    members_a = get_all_team_members(team_a)
    members_b = get_all_team_members(team_b)

    if len(members_a) != len(members_b):
        return False

    matched_b_indices = set()
    for ma in members_a:
        found_match = False
        for idx, mb in enumerate(members_b):
            if idx not in matched_b_indices and are_members_same(ma, mb):
                matched_b_indices.add(idx)
                found_match = True
                break
        if not found_match:
            return False

    return len(matched_b_indices) == len(members_b)


def validate_team_roster(
    form_data: Any,
    sport_cfg: dict[str, Any],
    user_dept: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, list[dict[str, Any]] | None, str | None]:
    """
    Validates all squad requirements strictly:
    1. Captain: Name, valid IITR Email (<name>@<dept>.iitr.ac.in), Student ID, Gender.
    2. Main Squad: All required main players, each with Name, IITR Email, Student ID, Gender.
    3. Substitutes: Up to sub_max. If any field in a substitute row is filled, Name, Email, and Student ID are all mandatory. If sub_max == 0, no subs allowed.
    4. Gender Rules:
       - Boys sports: 100% of all squad members (Captain, Main, Subs) MUST be 'Boy'.
       - Girls sports: 100% of all squad members (Captain, Main, Subs) MUST be 'Girl'.
       - Badminton (mix): Playing squad (Captain + 3 Main = 4 athletes) MUST have EXACTLY 2 Boys and 2 Girls.
       - Carrom (mix): Playing squad (Captain + 2 Main = 3 athletes) MUST have EXACTLY 2 Boys and 1 Girl.
    5. Internal Uniqueness: No student can be duplicated in the same team roster.
    
    Returns: (captain, main_players, substitutes, error_message)
    """
    sport_id = sport_cfg["id"]
    category = sport_cfg["category"]
    dept_norm = user_dept.strip().lower()

    # 1. Captain Validation (1 Required)
    c_name = str(form_data.get("captain_name", "")).strip()
    c_email = str(form_data.get("captain_email", "")).strip().lower()
    c_id = str(form_data.get("captain_id", "")).strip()
    c_gender = str(form_data.get("captain_gender", "")).strip()

    if not c_name:
        return None, None, None, "Captain Name is required."
    if not c_email:
        return None, None, None, "Captain Institute Email is required."
    if not c_id:
        return None, None, None, "Captain Student ID / Enrollment No. is required."
    if not c_gender:
        return None, None, None, "Captain Gender is required."

    c_dept = extract_department(c_email)
    if not c_dept:
        return None, None, None, f"Captain email '{c_email}' must be a valid IITR department student email (<name>@{dept_norm}.iitr.ac.in)."
    if c_dept != dept_norm:
        return None, None, None, f"Cross-Department Error: Captain belongs to '{c_dept.upper()}', but this team is strictly for '{dept_norm.upper()}'."

    # Gender check on Captain
    if category == "Boys" and c_gender != "Boy":
        return None, None, None, f"Strict Gender Rule: Only male athletes ('Boy') can be registered for {sport_cfg['name']}. Captain cannot be '{c_gender}'."
    if category == "Girls" and c_gender != "Girl":
        return None, None, None, f"Strict Gender Rule: Only female athletes ('Girl') can be registered for {sport_cfg['name']}. Captain cannot be '{c_gender}'."
    if category == "Mixed" and c_gender not in ("Boy", "Girl"):
        return None, None, None, "Captain Gender must be 'Boy' or 'Girl'."

    captain = {
        "name": c_name,
        "email": c_email,
        "student_id": c_id,
        "gender": c_gender,
        "role": "Captain",
    }

    # 2. Main Playing Squad Validation
    needed_main = sport_cfg["main_count"] - 1
    main_players = []

    for i in range(1, needed_main + 1):
        p_name = str(form_data.get(f"main_player_{i}_name", "")).strip()
        p_email = str(form_data.get(f"main_player_{i}_email", "")).strip().lower()
        p_id = str(form_data.get(f"main_player_{i}_id", "")).strip()
        p_gender = str(form_data.get(f"main_player_{i}_gender", "")).strip()

        if not p_name:
            return None, None, None, f"Main Player #{i} Name is required."
        if not p_email:
            return None, None, None, f"Main Player #{i} Institute Email is required."
        if not p_id:
            return None, None, None, f"Main Player #{i} Student ID / Enrollment No. is required."
        if not p_gender:
            return None, None, None, f"Main Player #{i} Gender is required."

        p_dept = extract_department(p_email)
        if not p_dept:
            return None, None, None, f"Main Player #{i} email '{p_email}' must be a valid IITR department student email (<name>@{dept_norm}.iitr.ac.in)."
        if p_dept != dept_norm:
            return None, None, None, f"Cross-Department Error: Main Player #{i} belongs to '{p_dept.upper()}', but this team is strictly for '{dept_norm.upper()}'."

        if category == "Boys" and p_gender != "Boy":
            return None, None, None, f"Strict Gender Rule: Only male athletes ('Boy') can be registered for {sport_cfg['name']}. Player #{i} '{p_name}' cannot be '{p_gender}'."
        if category == "Girls" and p_gender != "Girl":
            return None, None, None, f"Strict Gender Rule: Only female athletes ('Girl') can be registered for {sport_cfg['name']}. Player #{i} '{p_name}' cannot be '{p_gender}'."
        if category == "Mixed" and p_gender not in ("Boy", "Girl"):
            return None, None, None, f"Main Player #{i} Gender must be 'Boy' or 'Girl'."

        main_players.append({
            "name": p_name,
            "email": p_email,
            "student_id": p_id,
            "gender": p_gender,
            "role": f"Main Player {i}",
        })

    # 3. Substitutes Validation
    substitutes = []
    sub_max = sport_cfg.get("sub_max", 0)

    # Check for zero-sub sports (e.g. Carrom mix)
    if sub_max == 0:
        for k in form_data.keys():
            if k.startswith("sub_player_") and str(form_data.get(k, "")).strip():
                return None, None, None, f"Substitutes are strictly not permitted for {sport_cfg['name']}."
    else:
        for j in range(1, sub_max + 1):
            s_name = str(form_data.get(f"sub_player_{j}_name", "")).strip()
            s_email = str(form_data.get(f"sub_player_{j}_email", "")).strip().lower()
            s_id = str(form_data.get(f"sub_player_{j}_id", "")).strip()
            s_gender = str(form_data.get(f"sub_player_{j}_gender", "")).strip()

            has_any = bool(s_name or s_email or s_id)
            if has_any:
                if not s_name:
                    return None, None, None, f"Substitute #{j} Name is required if adding substitute #{j}."
                if not s_email:
                    return None, None, None, f"Substitute #{j} Institute Email is required if adding substitute #{j}."
                if not s_id:
                    return None, None, None, f"Substitute #{j} Student ID / Enrollment No. is required if adding substitute #{j}."
                if not s_gender:
                    return None, None, None, f"Substitute #{j} Gender is required if adding substitute #{j}."

                s_dept = extract_department(s_email)
                if not s_dept:
                    return None, None, None, f"Substitute #{j} email '{s_email}' must be a valid IITR department student email."
                if s_dept != dept_norm:
                    return None, None, None, f"Cross-Department Error: Substitute #{j} belongs to '{s_dept.upper()}', but this team is strictly for '{dept_norm.upper()}'."

                if category == "Boys" and s_gender != "Boy":
                    return None, None, None, f"Strict Gender Rule: Only male athletes ('Boy') can be registered for {sport_cfg['name']}. Substitute #{j} cannot be '{s_gender}'."
                if category == "Girls" and s_gender != "Girl":
                    return None, None, None, f"Strict Gender Rule: Only female athletes ('Girl') can be registered for {sport_cfg['name']}. Substitute #{j} cannot be '{s_gender}'."
                if category == "Mixed" and s_gender not in ("Boy", "Girl"):
                    return None, None, None, f"Substitute #{j} Gender must be 'Boy' or 'Girl'."

                substitutes.append({
                    "name": s_name,
                    "email": s_email,
                    "student_id": s_id,
                    "gender": s_gender,
                    "role": f"Substitute {len(substitutes) + 1}",
                })

    # 4. Mixed Sport Composition Rules
    playing_squad = [captain] + main_players
    if sport_id == "badminton_mix":
        boys_count = sum(1 for p in playing_squad if p["gender"] == "Boy")
        girls_count = sum(1 for p in playing_squad if p["gender"] == "Girl")
        if boys_count != 2 or girls_count != 2:
            return None, None, None, f"Badminton (mix) squad rule violation: The 4 playing athletes (Captain + Main squad) must include exactly 2 Boys and 2 Girls (found: {boys_count} Boys, {girls_count} Girls)."

        # Check substitutes: up to 2 substitutes, at most 1 boy and at most 1 girl
        sub_boys = sum(1 for s in substitutes if s["gender"] == "Boy")
        sub_girls = sum(1 for s in substitutes if s["gender"] == "Girl")
        if sub_boys > 1:
            return None, None, None, f"Badminton (mix) substitute rule violation: At most 1 Boy substitute is permitted (found: {sub_boys} Boys)."
        if sub_girls > 1:
            return None, None, None, f"Badminton (mix) substitute rule violation: At most 1 Girl substitute is permitted (found: {sub_girls} Girls)."

    elif sport_id == "carrom_mix":
        boys_count = sum(1 for p in playing_squad if p["gender"] == "Boy")
        girls_count = sum(1 for p in playing_squad if p["gender"] == "Girl")
        if boys_count != 1 or girls_count != 1:
            return None, None, None, f"Carrom (mix) squad rule violation: The 2 playing athletes (Captain + 1 Main Player) must include exactly 1 Boy and 1 Girl (found: {boys_count} Boy{'s' if boys_count != 1 else ''}, {girls_count} Girl{'s' if girls_count != 1 else ''})."

        # Check substitutes: up to 2 substitutes, at most 1 boy and at most 1 girl
        sub_boys = sum(1 for s in substitutes if s["gender"] == "Boy")
        sub_girls = sum(1 for s in substitutes if s["gender"] == "Girl")
        if sub_boys > 1:
            return None, None, None, f"Carrom (mix) substitute rule violation: At most 1 Boy substitute is permitted (found: {sub_boys} Boys)."
        if sub_girls > 1:
            return None, None, None, f"Carrom (mix) substitute rule violation: At most 1 Girl substitute is permitted (found: {sub_girls} Girls)."

    # 5. Internal Duplicate Athlete Check
    all_athletes = [captain] + main_players + substitutes
    for a in range(len(all_athletes)):
        for b in range(a + 1, len(all_athletes)):
            p1 = all_athletes[a]
            p2 = all_athletes[b]
            if p1["email"] == p2["email"]:
                return None, None, None, f"Duplicate Player Error: Email '{p1['email']}' is assigned to both {p1['role']} and {p2['role']}."
            if p1["student_id"] == p2["student_id"]:
                return None, None, None, f"Duplicate Player Error: Student ID '{p1['student_id']}' is assigned to both {p1['role']} ('{p1['name']}') and {p2['role']} ('{p2['name']}')."
            if " ".join(p1["name"].lower().split()) == " ".join(p2["name"].lower().split()):
                return None, None, None, f"Duplicate Player Error: '{p1['name']}' is added multiple times in the same squad ({p1['role']} and {p2['role']})."

    return captain, main_players, substitutes, None


async def _load_dept_teams(dept: str) -> dict[str, list[dict[str, Any]]]:
    """
    Reads teams from the department collection in 'departments' database.
    Returns a dictionary mapping each sport_id to a list of registered team objects.
    Each team object has a guaranteed 'team_id'.
    """
    col = _get_dept_collection(dept)
    teams_by_sport: dict[str, list[dict[str, Any]]] = {sid: [] for sid in SPORTS_CONFIG}

    try:
        # Track sports that are explicitly configured in the events document
        sports_in_events = set()

        # 1. Primary storage: document '_id: events' where keys are sport_ids
        events_doc = await col.find_one({"_id": "events"})
        if events_doc:
            for sport_id in SPORTS_CONFIG:
                if sport_id in events_doc:
                    sports_in_events.add(sport_id)
                    val = events_doc.get(sport_id)
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and (item.get("captain") or item.get("created_by") or item.get("status")):
                                if not item.get("team_id"):
                                    item["team_id"] = f"{sport_id}_{uuid.uuid4().hex[:8]}"
                                if not any(t.get("team_id") == item["team_id"] for t in teams_by_sport[sport_id]):
                                    teams_by_sport[sport_id].append(item)
                    elif isinstance(val, dict) and (val.get("captain") or val.get("created_by") or val.get("status")):
                        if not val.get("team_id"):
                            val["team_id"] = f"{sport_id}_{uuid.uuid4().hex[:8]}"
                        if not any(t.get("team_id") == val["team_id"] for t in teams_by_sport[sport_id]):
                            teams_by_sport[sport_id].append(val)

        # 2. Check individual documents with '_id == sport_id' ONLY for sports NOT in events_doc
        sports_to_check = [sid for sid in SPORTS_CONFIG if sid not in sports_in_events]
        if sports_to_check:
            docs = await col.find({"_id": {"$in": sports_to_check}}).to_list(length=None)
            for doc in docs:
                sid = doc.get("_id")
                if sid not in teams_by_sport:
                    teams_by_sport[sid] = []

                if "teams" in doc and isinstance(doc["teams"], list):
                    doc_teams = doc["teams"]
                elif sid in doc and isinstance(doc[sid], list):
                    doc_teams = doc[sid]
                else:
                    doc_teams = []

                if isinstance(doc_teams, list):
                    for item in doc_teams:
                        if isinstance(item, dict) and (item.get("captain") or item.get("created_by") or item.get("status")):
                            if not item.get("team_id"):
                                item["team_id"] = f"{sid}_{uuid.uuid4().hex[:8]}"
                            if not any(t.get("team_id") == item["team_id"] for t in teams_by_sport[sid]):
                                teams_by_sport[sid].append(item)

    except Exception as exc:
        print(f"Warning: Failed to load dept teams: {exc}")

    return teams_by_sport


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    sport: str | None = None,
    action: str | None = None,
    team_id: str | None = None,
    msg: str | None = None,
    err: str | None = None,
):
    """
    Unified entry route:
    1. Handles Google OAuth callback if code or error query parameter is present.
    2. Enforces that only students from AMSC, PE, and PPE can access.
    3. Strictly isolates student view to their own department's collection.
    4. Shows available sports grid with team registration status for their department.
    5. Allows multiple teams per sport as long as rosters are not identical.
    6. Dynamically shows list of existing teams, registration form, or edit form.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    oauth_error = request.query_params.get("error")
    if code or oauth_error:
        from routes.auth import auth_callback
        return await auth_callback(request, code=code, state=state, error=oauth_error)

    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Department is strictly locked to the student's authenticated department
    active_dept = _get_user_dept(user)
    if active_dept not in ALLOWED_DEPARTMENTS:
        request.session.clear()
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "rejected_email": user.get("email"),
                "detected_dept": active_dept.upper() if active_dept else "None / Staff",
                "error_title": "Department Not Competing",
                "error_message": "Access restricted: Only students from AMSC, PE, and PPE can access the portal.",
                "reason": "Your account department is not eligible for this competition.",
            },
            status_code=403,
        )

    # Load teams registered STRICTLY for this student's department
    created_teams_by_sport = await _load_dept_teams(active_dept)
    total_dept_teams_count = sum(len(t_list) for t_list in created_teams_by_sport.values())

    # Selected sport (defaults to cricket_boys or first available)
    selected_sport_id = sport if sport in SPORTS_CONFIG else "cricket_boys"
    selected_sport = SPORTS_CONFIG[selected_sport_id]

    # Existing teams list for this selected sport
    existing_teams = created_teams_by_sport.get(selected_sport_id, [])

    # Editing mode flag
    user_email = user.get("email", "").lower()
    editing_team = None
    is_editing = False

    user_formed_team = next((t for t in existing_teams if t.get("created_by") == user_email), None)
    has_user_formed_team = user_formed_team is not None

    user_registered_sports = {
        sid for sid, t_list in created_teams_by_sport.items()
        if any(t.get("created_by") == user_email for t in t_list)
    }

    if action == "edit" and team_id:
        editing_team = next((t for t in existing_teams if t.get("team_id") == team_id), None)
        if editing_team and editing_team.get("created_by") == user_email:
            is_editing = True

    # Messages
    flash_error = request.session.pop("flash_error", None)
    success_message = MESSAGES.get(msg or "")
    error_message = flash_error or ERRORS.get(err or "")

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "user": user,
            "active_dept": active_dept,
            "active_dept_upper": active_dept.upper(),
            "sports": SPORTS_CONFIG,
            "selected_sport_id": selected_sport_id,
            "selected_sport": selected_sport,
            "total_dept_teams_count": total_dept_teams_count,
            "created_teams_by_sport": created_teams_by_sport,
            "existing_teams": existing_teams,
            "user_formed_team": user_formed_team,
            "has_user_formed_team": has_user_formed_team,
            "user_registered_sports": user_registered_sports,
            "editing_team": editing_team,
            "is_editing": is_editing,
            "success_message": success_message,
            "error_message": error_message,
        },
    )


@router.post("/register")
async def create_team(request: Request):
    """
    Handles team creation without requiring any team_name.
    Everyone gets to form a team for each sport in each department whether they are
    already within a team or not. If none of the members are different from an existing
    team for this sport, rejects and notifies that the team already exists.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_dept = _get_user_dept(user)
    if user_dept not in ALLOWED_DEPARTMENTS:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    user_email = user.get("email", "").lower()
    form_data = await request.form()

    # Department is strictly user's authenticated department (cannot be spoofed)
    dept = user_dept
    sport_id = str(form_data.get("sport_id", "")).strip()

    if sport_id not in SPORTS_CONFIG:
        return RedirectResponse(url="/register?err=invalid_sport", status_code=303)

    # Load existing teams for this department and sport
    existing_dept_teams = await _load_dept_teams(dept)
    teams_for_this_sport = existing_dept_teams.get(sport_id, [])

    # Check rule: Each person can form only 1 team of their own at max per sport per department
    has_existing_own_team = any(
        t.get("created_by") == user_email
        for t in teams_for_this_sport
    )
    if has_existing_own_team:
        return RedirectResponse(
            url=f"/register?sport={sport_id}&err=user_already_has_team#sport-section",
            status_code=303,
        )

    sport_cfg = SPORTS_CONFIG[sport_id]
    captain, main_players, substitutes, val_error = validate_team_roster(form_data, sport_cfg, dept)
    if val_error:
        request.session["flash_error"] = val_error
        return RedirectResponse(
            url=f"/register?sport={sport_id}#sport-section",
            status_code=303,
        )

    # Build Team Record with unique team_id
    new_team_id = f"team_{uuid.uuid4().hex[:10]}"
    team_record = {
        "team_id": new_team_id,
        "sport_id": sport_id,
        "sport_name": sport_cfg["name"],
        "category": sport_cfg["category"],
        "department": dept.upper(),
        "created_by": user_email,
        "created_by_name": user.get("name", "Athlete"),
        "captain": captain,
        "main_players": main_players,
        "substitutes": substitutes,
        "total_playing": 1 + len(main_players),
        "total_substitutes": len(substitutes),
        "total_strength": 1 + len(main_players) + len(substitutes),
        "status": "Registered",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Check rule: "however if none of the members are different then do not add the team just notify that the team already exists."
    for existing_t in teams_for_this_sport:
        if are_team_rosters_identical(team_record, existing_t):
            return RedirectResponse(
                url=f"/register?sport={sport_id}&err=duplicate_roster#sport-section",
                status_code=303,
            )

    updated_teams_list = teams_for_this_sport + [team_record]

    try:
        col = _get_dept_collection(dept)
        # 1. Update in events document
        await col.update_one(
            {"_id": "events"},
            {
                "$set": {sport_id: updated_teams_list, "department": dept, "updated_at": datetime.utcnow().isoformat()},
                "$unset": {"team": ""},
            },
            upsert=True,
        )
        # 2. Update in individual sport document
        await col.update_one(
            {"_id": sport_id},
            {
                "$set": {
                    "_id": sport_id,
                    "sport_id": sport_id,
                    "sport_name": sport_cfg["name"],
                    "teams": updated_teams_list,
                    sport_id: updated_teams_list,
                    "department": dept,
                    "updated_at": datetime.utcnow().isoformat(),
                },
                "$unset": {"team": ""},
            },
            upsert=True,
        )
    except Exception as exc:
        print(f"Warning: Team registration failed: {exc}")
        return RedirectResponse(
            url=f"/register?sport={sport_id}&err=db_error#sport-section",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/register?sport={sport_id}&msg=team_created#sport-section",
        status_code=303,
    )


@router.post("/register/edit")
async def edit_team(request: Request):
    """
    Handle updating an existing team directly in the department collection.
    Only the team creator can perform edits.
    Validates that the updated roster is not identical to another registered team.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_dept = _get_user_dept(user)
    if user_dept not in ALLOWED_DEPARTMENTS:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    user_email = user.get("email", "").lower()
    form_data = await request.form()

    dept = user_dept
    sport_id = str(form_data.get("sport_id", "")).strip()
    team_id = str(form_data.get("team_id", "")).strip()

    if sport_id not in SPORTS_CONFIG:
        return RedirectResponse(url="/register", status_code=303)

    sport_cfg = SPORTS_CONFIG[sport_id]
    existing_dept_teams = await _load_dept_teams(dept)
    teams_for_this_sport = existing_dept_teams.get(sport_id, [])

    # Find the target team by team_id
    target_team = next((t for t in teams_for_this_sport if t.get("team_id") == team_id), None)
    if not target_team:
        return RedirectResponse(url=f"/register?sport={sport_id}&err=team_not_found#sport-section", status_code=303)

    if target_team.get("created_by") != user_email:
        return RedirectResponse(url=f"/register?sport={sport_id}&err=unauthorized#sport-section", status_code=303)

    captain, main_players, substitutes, val_error = validate_team_roster(form_data, sport_cfg, dept)
    if val_error:
        request.session["flash_error"] = val_error
        return RedirectResponse(
            url=f"/register?sport={sport_id}&action=edit&team_id={team_id}#sport-section",
            status_code=303,
        )

    updated_team = {
        **target_team,
        "team_id": team_id,
        "captain": captain,
        "main_players": main_players,
        "substitutes": substitutes,
        "total_playing": 1 + len(main_players),
        "total_substitutes": len(substitutes),
        "total_strength": 1 + len(main_players) + len(substitutes),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Check if updated team roster matches another existing team in this sport
    for other_t in teams_for_this_sport:
        if other_t.get("team_id") != team_id and are_team_rosters_identical(updated_team, other_t):
            return RedirectResponse(
                url=f"/register?sport={sport_id}&action=edit&team_id={team_id}&err=duplicate_roster#sport-section",
                status_code=303,
            )

    updated_teams_list = [
        updated_team if t.get("team_id") == team_id else t
        for t in teams_for_this_sport
    ]

    try:
        col = _get_dept_collection(dept)
        await col.update_one(
            {"_id": "events"},
            {
                "$set": {sport_id: updated_teams_list, "updated_at": datetime.utcnow().isoformat()},
                "$unset": {"team": ""},
            },
            upsert=True,
        )
        await col.update_one(
            {"_id": sport_id},
            {
                "$set": {
                    "teams": updated_teams_list,
                    sport_id: updated_teams_list,
                    "updated_at": datetime.utcnow().isoformat(),
                },
                "$unset": {"team": ""},
            },
            upsert=True,
        )
    except Exception as exc:
        print(f"Warning: Team update failed: {exc}")
        return RedirectResponse(url=f"/register?sport={sport_id}&err=db_error", status_code=303)

    return RedirectResponse(
        url=f"/register?sport={sport_id}&msg=team_updated#sport-section",
        status_code=303,
    )


@router.post("/register/delete")
async def delete_team(request: Request):
    """
    Handle deleting an existing team from the department collection.
    Only the team creator can perform deletion.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_dept = _get_user_dept(user)
    if user_dept not in ALLOWED_DEPARTMENTS:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    user_email = user.get("email", "").lower()
    form_data = await request.form()

    dept = user_dept
    sport_id = str(form_data.get("sport_id", "cricket_boys")).strip()
    team_id = str(form_data.get("team_id", "")).strip()

    existing_dept_teams = await _load_dept_teams(dept)
    teams_for_this_sport = existing_dept_teams.get(sport_id, [])

    target_team = next((t for t in teams_for_this_sport if t.get("team_id") == team_id), None)
    if not target_team:
        # Fallback: check if the user has a team created by them in this sport
        target_team = next((t for t in teams_for_this_sport if t.get("created_by") == user_email), None)
        if target_team:
            team_id = target_team.get("team_id")
        else:
            return RedirectResponse(url=f"/register?sport={sport_id}&err=team_not_found#sport-section", status_code=303)

    if target_team.get("created_by") != user_email:
        return RedirectResponse(url=f"/register?sport={sport_id}&err=unauthorized#sport-section", status_code=303)

    remaining_teams = [t for t in teams_for_this_sport if t.get("team_id") != team_id]

    try:
        col = _get_dept_collection(dept)
        if remaining_teams:
            # 1. Update events document with remaining teams
            await col.update_one(
                {"_id": "events"},
                {
                    "$set": {sport_id: remaining_teams, "updated_at": datetime.utcnow().isoformat()},
                    "$unset": {"team": ""},
                },
                upsert=True,
            )
            # 2. Update individual sport document with remaining teams
            await col.update_one(
                {"_id": sport_id},
                {
                    "$set": {
                        "teams": remaining_teams,
                        sport_id: remaining_teams,
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                    "$unset": {"team": ""},
                },
                upsert=True,
            )
        else:
            # When NO teams remain for this sport, physically delete the sport document and clean events
            # 1. Hard delete the sport document from the collection
            await col.delete_one({"_id": sport_id})

            # 2. Unset the sport field completely from the events document
            await col.update_one(
                {"_id": "events"},
                {
                    "$unset": {sport_id: "", "team": ""},
                    "$set": {"updated_at": datetime.utcnow().isoformat()},
                },
            )

            # 3. If events document has no more sports registered at all, clean it up completely
            ev_doc = await col.find_one({"_id": "events"})
            if ev_doc:
                active_sport_keys = [k for k in ev_doc if k in SPORTS_CONFIG]
                if not active_sport_keys:
                    await col.delete_one({"_id": "events"})
    except Exception as exc:
        print(f"Warning: Database delete failed: {exc}")
        return RedirectResponse(url=f"/register?sport={sport_id}&err=db_error", status_code=303)

    return RedirectResponse(
        url=f"/register?sport={sport_id}&msg=team_deleted#sport-section",
        status_code=303,
    )


# Compatibility redirects
@router.get("/teams")
async def list_teams_redirect():
    return RedirectResponse(url="/register", status_code=303)


@router.get("/teams/{team_id}")
async def view_team_redirect(team_id: str):
    return RedirectResponse(url="/register", status_code=303)


@router.get("/teams/{team_id}/edit")
async def edit_team_redirect(team_id: str):
    return RedirectResponse(url="/register?action=edit", status_code=303)


@router.post("/teams/{team_id}/delete")
async def delete_team_redirect(team_id: str):
    return RedirectResponse(url="/register", status_code=303)
