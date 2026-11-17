from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_librarian_user(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (getattr(user, "role", None) == "LIBRARIAN" or user.is_staff or user.is_superuser)
    )


class IsLibrarian(BasePermission):
    def has_permission(self, request, view):
        return is_librarian_user(request.user)


class IsLibrarianOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_librarian_user(request.user)