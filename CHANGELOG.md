# Changelog

## [0.1.8](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.7...weevr-cli-v0.1.8) (2026-04-03)


### Features

* **cli:** add plugin system with entry-point discovery and management commands ([#18](https://github.com/ardent-data/weevr-cli/issues/18)) ([b4d84ee](https://github.com/ardent-data/weevr-cli/commit/b4d84ee3f187248fa16b69f00cfb76b2194f5a78))

## [0.1.7](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.6...weevr-cli-v0.1.7) (2026-04-03)


### Features

* add status and list commands ([#15](https://github.com/ardent-data/weevr-cli/issues/15)) ([f03cba8](https://github.com/ardent-data/weevr-cli/commit/f03cba87d65f0163b3f632960bbe0325662415d2))

## [0.1.6](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.5...weevr-cli-v0.1.6) (2026-04-03)


### Features

* **deploy:** add deploy command with OneLake sync ([#13](https://github.com/ardent-data/weevr-cli/issues/13)) ([601a63b](https://github.com/ardent-data/weevr-cli/commit/601a63bc52b4f07aaf965800e792921adcda595b))

## [0.1.5](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.4...weevr-cli-v0.1.5) (2026-04-03)


### Features

* **cli:** add validate and schema commands with JSON schema validation and ref checking ([#12](https://github.com/ardent-data/weevr-cli/issues/12)) ([8a9c94a](https://github.com/ardent-data/weevr-cli/commit/8a9c94ab41d9a9d1b47668bb1355c02de0cf0254))


### Bug Fixes

* **ci:** use frozen lockfile to tolerate Release Please version bumps ([#10](https://github.com/ardent-data/weevr-cli/issues/10)) ([d2efed5](https://github.com/ardent-data/weevr-cli/commit/d2efed529560d0aca4b23b1e32a21e32368dcab4))

## [0.1.4](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.3...weevr-cli-v0.1.4) (2026-04-03)


### Bug Fixes

* **init:** adopt .weevr project root model matching engine conventions ([#8](https://github.com/ardent-data/weevr-cli/issues/8)) ([5f089c5](https://github.com/ardent-data/weevr-cli/commit/5f089c5456cfc85e9401f3c20b803b732a7c0610))

## [0.1.3](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.2...weevr-cli-v0.1.3) (2026-04-02)


### Bug Fixes

* **templates:** align YAML with engine format and remove opinionated init structure ([#6](https://github.com/ardent-data/weevr-cli/issues/6)) ([8b651b0](https://github.com/ardent-data/weevr-cli/commit/8b651b099b3679b6120445e0d04f2205fb86c832))

## [0.1.2](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.1...weevr-cli-v0.1.2) (2026-04-02)


### Features

* add embedded YAML templates for thread, weave, and loom files ([c6803d6](https://github.com/ardent-data/weevr-cli/commit/c6803d6792ece7f7d6b06e8c0e146c096f8ca502))
* add interactive wizard to init command ([9db6cc9](https://github.com/ardent-data/weevr-cli/commit/9db6cc99fbd611ee71924e56c9e668cf84de87a7))
* **cli:** implement init and new commands with templates and interactive wizard ([b71b16b](https://github.com/ardent-data/weevr-cli/commit/b71b16b13eeaa96467c3e210f6288b5d10ff7bcb))
* implement init command with project scaffolding ([43c2ca4](https://github.com/ardent-data/weevr-cli/commit/43c2ca48dfa23d4e2c6dd4ef400672f4ad4d2a75))
* implement new command for generating weevr files ([8330864](https://github.com/ardent-data/weevr-cli/commit/83308644c985a649508fc1920ac11d27f646f126))

## [0.1.1](https://github.com/ardent-data/weevr-cli/compare/weevr-cli-v0.1.0...weevr-cli-v0.1.1) (2026-04-02)


### Features

* add AppState dataclass for Typer context ([c533363](https://github.com/ardent-data/weevr-cli/commit/c533363fcbf38b132802f10fb0b47cc704f8ace7))
* add config dataclasses and YAML loading ([dfd95a3](https://github.com/ardent-data/weevr-cli/commit/dfd95a37b9f9917bdf818e44201bc6b66b153423))
* add global --json flag, config loading, and AppState to root callback ([2273bd0](https://github.com/ardent-data/weevr-cli/commit/2273bd03bbcba15818952220d6b7150be902cc28))
* add output helpers for Rich and JSON modes ([921ee11](https://github.com/ardent-data/weevr-cli/commit/921ee1126638b9e73b17d72fb32dcac22dce3b99))
* **cli:** add CLI foundation with config loading, JSON output, and Rich diagnostics ([1c3373f](https://github.com/ardent-data/weevr-cli/commit/1c3373f3c63e1030b7c864e59999dfbec7e514cd))
* **project:** scaffold weevr-cli repository ([35d4fcd](https://github.com/ardent-data/weevr-cli/commit/35d4fcda4580454e54407a55462319015dc9eb9f))
* read version from package metadata instead of hardcoded string ([831f9f4](https://github.com/ardent-data/weevr-cli/commit/831f9f4e0d9b67960f70aea782d831da805f29e9))


### Bug Fixes

* **ci:** add contents read permission to CodeQL workflow ([a9a8707](https://github.com/ardent-data/weevr-cli/commit/a9a8707d0c4458bcc28456a8d820f4b1fa904bca))
* **ci:** commit uv.lock for reproducible CI builds ([edef632](https://github.com/ardent-data/weevr-cli/commit/edef632b4ccdd2e52b19db535f3d9e7e388004d9))


### Documentation

* recommend uv over pipx for installation ([bac8b41](https://github.com/ardent-data/weevr-cli/commit/bac8b411d06fa75836ac7e586da224863f5fad44))
