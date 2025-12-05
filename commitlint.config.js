/**
 * Commitlint configuration for semantic versioning
 * 
 * Commit message format: <type>(<scope>): <subject>
 * 
 * Types that trigger version bumps:
 *   - feat:     New feature (minor version bump)
 *   - fix:      Bug fix (patch version bump)
 *   - perf:     Performance improvement (patch version bump)
 * 
 * Types that don't trigger version bumps:
 *   - docs:     Documentation only
 *   - style:    Code style (formatting, semicolons, etc.)
 *   - refactor: Code refactoring (no feature/fix)
 *   - test:     Adding/updating tests
 *   - chore:    Maintenance tasks
 *   - ci:       CI/CD changes
 *   - build:    Build system changes
 *   - revert:   Reverting previous commits
 * 
 * Breaking changes:
 *   Add "BREAKING CHANGE:" in the commit body or "!" after type
 *   Example: feat!: new API endpoint
 *   This triggers a major version bump
 * 
 * Examples:
 *   feat(auth): add OAuth2 support
 *   fix(network): resolve connection timeout issue
 *   docs: update README with deployment instructions
 *   refactor(backend): simplify database queries
 *   feat!: redesign API endpoints (breaking change)
 */

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Type must be one of the allowed values
    'type-enum': [
      2,
      'always',
      [
        'feat',     // New feature (MINOR version bump)
        'fix',      // Bug fix (PATCH version bump)
        'docs',     // Documentation only changes
        'style',    // Code style changes (formatting, semicolons, etc.)
        'refactor', // Code refactoring (no feature change, no bug fix)
        'perf',     // Performance improvements (PATCH version bump)
        'test',     // Adding or updating tests
        'chore',    // Maintenance tasks, dependency updates
        'ci',       // CI/CD configuration changes
        'build',    // Build system or external dependency changes
        'revert',   // Reverting a previous commit
        'lint',     // Linting fixes (custom type for this project)
        'config',   // Configuration file changes
        'wip'       // Work in progress (should be squashed before merge)
      ]
    ],
    // Type must be lowercase
    'type-case': [2, 'always', 'lower-case'],
    // Type cannot be empty
    'type-empty': [2, 'never'],
    // Scope should be lowercase if provided
    'scope-case': [2, 'always', 'lower-case'],
    // Subject cannot be empty
    'subject-empty': [2, 'never'],
    // Subject should not end with a period
    'subject-full-stop': [2, 'never', '.'],
    // Subject should be sentence case or lower case
    'subject-case': [
      2,
      'never',
      ['sentence-case', 'start-case', 'pascal-case', 'upper-case']
    ],
    // Header (type + scope + subject) max length
    'header-max-length': [2, 'always', 100],
    // Body max line length
    'body-max-line-length': [2, 'always', 200],
    // Footer max line length
    'footer-max-line-length': [2, 'always', 200]
  },
  // Help messages shown when validation fails
  helpUrl: 'https://www.conventionalcommits.org/'
};

