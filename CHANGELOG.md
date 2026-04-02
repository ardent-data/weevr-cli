# Changelog

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
