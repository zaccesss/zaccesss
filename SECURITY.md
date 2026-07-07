# Security Policy

> Public version of this policy: https://isaacadjei.me/security-policy

This repository is public. It holds my GitHub profile README, the generator that
builds it and the SVGs it produces. The generator reads public GitHub statistics
with a read only token, so it can never change anything.

## Reporting a vulnerability

Please report anything security relevant privately, not in a public issue.

- Email contact@isaacadjei.me with the details and steps to reproduce.
- Expect an acknowledgement within a few days.

## What lives here and what does not

- No secret value is ever committed to this repository. The only credential,
  `ACCESS_TOKEN`, exists solely as a GitHub Actions secret.
- `ACCESS_TOKEN` is a fine grained token scoped to read only, covering the account
  and repository statistics the generator needs. It cannot write to any repository.
- The workflow's write access to this repo comes from the built in `GITHUB_TOKEN`,
  scoped to this repository alone, and is only used to commit the regenerated SVGs.

## If a credential is exposed

Rotate first, investigate second. The token is narrowly scoped and can be revoked
and reissued without downtime, because the build simply re-runs against the new token.

1. Revoke the exposed token in GitHub fine grained token settings.
2. Generate a replacement with the same minimal read only scope.
3. Update the `ACCESS_TOKEN` Actions secret.
4. Run the build by hand from the Actions tab to confirm it still works.
