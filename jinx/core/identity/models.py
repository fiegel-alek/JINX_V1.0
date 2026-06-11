"""Identity and RBAC primitives for JINX."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Permission:
    name: str
    description: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("permission name is required")
        if not self.description:
            raise ValueError("permission description is required")


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    permissions: frozenset[str]
    description: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("role name is required")
        if not self.description:
            raise ValueError("role description is required")


@dataclass(frozen=True, slots=True)
class User:
    username: str
    roles: frozenset[str]
    display_name: str
    id: str = field(default_factory=lambda: f"user-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.username:
            raise ValueError("username is required")
        if not self.display_name:
            raise ValueError("display_name is required")
        if not self.roles:
            raise ValueError("user requires at least one role")


@dataclass(slots=True)
class AccessControl:
    roles: dict[str, Role] = field(default_factory=dict)
    users: dict[str, User] = field(default_factory=dict)

    def register_role(self, role: Role) -> None:
        if role.name in self.roles:
            raise ValueError(f"role already registered: {role.name}")
        self.roles[role.name] = role

    def register_user(self, user: User) -> None:
        missing_roles = user.roles.difference(self.roles)
        if missing_roles:
            raise ValueError(f"user references unknown roles: {','.join(sorted(missing_roles))}")
        if user.id in self.users:
            raise ValueError(f"user already registered: {user.id}")
        self.users[user.id] = user

    def permissions_for_user(self, user_id: str) -> frozenset[str]:
        user = self._user(user_id)
        permissions: set[str] = set()
        for role_name in user.roles:
            permissions.update(self.roles[role_name].permissions)
        return frozenset(permissions)

    def may(self, user_id: str, permission: str) -> bool:
        return permission in self.permissions_for_user(user_id)

    def _user(self, user_id: str) -> User:
        try:
            return self.users[user_id]
        except KeyError as exc:
            raise KeyError(f"user not registered: {user_id}") from exc
