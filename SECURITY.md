# Security policy

## Supported versions

Security fixes are provided for the latest release and the default
branch. Older releases are not supported. Upgrade before reporting
an issue that may already be fixed.

## Reporting a vulnerability

Do not open a public issue, pull request, or discussion for a suspected
vulnerability.

Use either private channel:

- **GitHub Security Advisories.** Open a private report from this
  repository's Security tab, **Report a vulnerability**. This is the
  preferred channel.
- **Email.** `jechenmailman@gmail.com`, with a subject line that begins
  with `[SECURITY]`.

Include the affected version, platform, impact, and steps to reproduce.
Do not attach credentials, tokens, or unredacted logs.

The maintainers aim to acknowledge a report within 5 business days, and
to coordinate a fix and disclosure within 90 days. There is no bug-bounty
promise.

## Operational notes

Starting a test writes the user detail dictionary and the keyword arguments
to ``~/.je_load_density/logs/LoadDensity.log`` at INFO. That dictionary can
contain passwords, bearer tokens, and connection strings. Do not share the
log, and do not leave live secrets in a test definition that will be logged.

Point a load test only at a system you are allowed to load.
