class DomainError(Exception):
    """Base class for business-rule violations raised from the domain layer."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, entity_id: str):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} not found: {entity_id}")


class EntityAlreadyExistsError(DomainError):
    def __init__(self, entity_name: str, field: str, value: str):
        self.entity_name = entity_name
        self.field = field
        self.value = value
        super().__init__(f"{entity_name} already exists with {field}={value}")


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__("Invalid email or password")


class PermissionDeniedError(DomainError):
    def __init__(self, action: str):
        self.action = action
        super().__init__(f"Permission denied for action: {action}")
