<!--
  This library exists to support Home Assistant integrations. Changes
  here should be motivated by a concrete need in Home Assistant Core. Every
  change must therefore be accompanied by a corresponding **draft** PR in the
  home-assistant/core repository that consumes it, so reviewers can see how the
  change is actually used.

  Note: there is no requirement to implement a given protocol or its codes in
  this library. An integration may use a separate, dedicated library instead,
  as long as that library depends on this one for the underlying types. This
  library's primary role is to provide the shared, foundational types.
-->

## Proposed change

<!-- Describe what this PR changes and why. -->

## Type of change

<!--
  Check the box(es) that apply. The matching label is applied to the PR
  automatically and determines the release notes section and version bump.
  Do not edit the text of the options.
-->

- [ ] Breaking change (changes existing public API or behavior in an incompatible way)
- [ ] New feature (new protocol, device codes, or functionality)
- [ ] Enhancement (improves existing code without adding new functionality)
- [ ] Bugfix (fixes an issue in existing code)
- [ ] Dependency upgrade
- [ ] Maintenance (cleanup, tooling, or other housekeeping)
- [ ] CI (GitHub Actions workflows)
- [ ] Documentation (documentation-only change)

## Additional information

<!--
  Link to the draft PR in home-assistant/core that uses this change. This is
  required: it demonstrates the real-world usage that motivates the change.
-->

- Link to core pull request: <!-- e.g. https://github.com/home-assistant/core/pull/XXXXX (draft) -->

## Checklist

- [ ] I have linked a draft PR in `home-assistant/core` that consumes this change.
- [ ] Lint, format, and type checks pass (`prek --all-files`).
- [ ] Tests pass (`pytest`).
