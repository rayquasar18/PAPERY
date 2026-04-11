"""Business logic layer — orchestration, validation, and domain rules.

Services delegate all data access to the repository layer
(``app.repositories``) and focus exclusively on business logic.

Available services:
- ``AuthService`` — registration, login, logout, token rotation, email verification
- ``UserService`` — profile viewing, editing, avatar management, account deletion
"""
