from django_keycloak_sso.sso.authentication import CustomUser


def check_roles_in_data(roles: list, user_roles: list) -> bool:
    data_titles = {item['id'] for item in user_roles}
    return all(role in data_titles for role in roles)


def check_groups(groups: list, user_groups: list) -> bool:
    groups_data = {item['group']['id'] for item in user_groups}
    access_status = all(group in groups_data for group in groups)
    return access_status


def check_groups_in_data(groups: list, roles: list, user_groups: list) -> bool:
    groups_data = {item['group']['id'] for item in user_groups}
    roles_data = {item['role'] for item in user_groups}
    access_status = all(group in groups_data for group in groups) and all(role in roles_data for role in roles)
    return access_status


def check_user_permission_access(
        user: CustomUser,
        role_titles: list[str],
        group_titles: list[str],
        group_roles: list[str],
        match_group_roles: bool = False,
) -> bool:
    if not isinstance(user, CustomUser):
        return False

    # Normalize inputs
    role_titles = [r.lower() for r in role_titles]
    group_titles = [g.lower() for g in group_titles]
    group_roles = [r.lower() for r in group_roles]
    user_roles = [r.lower() for r in user.roles]
    user_client_roles = [r.lower() for r in user.client_roles]

    # Parse groups from user.groups (e.g., '/group_1/managers')
    parsed_user_groups = []
    for group_path in user.groups:
        parts = group_path.strip("/").split("/")
        if len(parts) == 2:
            group, role = parts
            role = role[:-1] if role.endswith('s') else role
            parsed_user_groups.append((group.lower(), role.lower()))

    # Rule 1: user must have all role_titles in either roles or client_roles
    for required_role in role_titles:
        if required_role not in user_roles and required_role not in user_client_roles:
            return False

    # Rule 2: user must be a member of ALL group_titles (match just the group name)
    user_group_names = [group for group, _ in parsed_user_groups]
    for required_group in group_titles:
        if required_group not in user_group_names:
            return False

    # Rule 3: user must be in at least one group where their role matches one of group_roles
    if group_roles:
        matched = False
        for group, role in parsed_user_groups:
            if match_group_roles:
                if group in group_titles and role in group_roles:
                    matched = True
                    break
            else:
                if role in group_roles:
                    matched = True
                    break
        if not matched:
            return False

    # If no matching group-role combo was found
    return True
