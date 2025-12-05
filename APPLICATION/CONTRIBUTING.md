# Contributing to Audity

We are excited that you are considering contributing to Audity! Here are some guidelines to help you get started.

## Code of Conduct

By contributing to this project, you are expected to uphold our code of conduct, which ensures a respectful and productive environment for all participants.

## Naming Conventions

### Constants
- Use `UPPER_SNAKE_CASE` for constants.
- Example: `MAX_RETRY_COUNT`

### Variables
- Use `snake_case` for local variables and attributes.
- Example: `user_count`

### Functions and Methods
- Use `snake_case` for functions and methods.
- Example: `update_user_profile`

### Classes and Enums
- Use `PascalCase` for class and enum names.
- Example: `UserProfile`

### Modules
- Module names should be in `snake_case`.
- Example: `data_processing`

### Files
- Files should be named in `snake_case`.
- Example: `user_management.rs`

## Branch Naming Conventions

To keep our repository organized and to facilitate understanding of the history and purpose of different branches, please follow these naming conventions when creating branches:

- **Feature Branches**: Prefix with `feature/`, followed by a short descriptor related to the feature you are working on.
  - Example: `feature/add-login`

- **Bugfix Branches**: Prefix with `bugfix/`, followed by a descriptor of the bug you are addressing.
  - Example: `bugfix/resolve-login-issue`

- **Hotfix Branches**: For urgent fixes, use `hotfix/`, followed by a description of the critical issue being fixed.
  - Example: `hotfix/correct-security-vulnerability`

- **Release Branches**: For release preparation, use `release/`, followed by the version number.
  - Example: `release/v1.0.0`

- **Documentation Branches**: For updates to documentation, use `docs/`, followed by a short description.
  - Example: `docs/update-contributing-guidelines`

Please ensure that your branch names are descriptive, succinct, and relevant to the changes they contain.

## General Principles

- **Clarity over brevity**: Names should be descriptive and provide a clear indication of their use.
- **Consistency**: All contributors should follow the same conventions to maintain code uniformity.
- **Documentation**: Comment complex parts of the code to aid in understanding and maintenance.

## Commenting

- **Code Comments**: Explain the "why" behind complex code decisions, not just the "how".
- **Docstrings**: Use docstrings to describe functions, parameters, return values, and provide usage examples.

## Submitting Contributions

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## Testing

Ensure that your changes pass all existing tests and, if possible, write new tests to cover your feature or bug fix.

## Questions?

If you have questions or need assistance, feel free to open an issue to ask for help.

Thank you for your contribution to Audity!
