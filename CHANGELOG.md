# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.0] - 2025-01-29

### Changed

- Single source of truth for version: root `VERSION` file; backend, frontend, Android, installers and website read or are updated from it.
- Release workflow: bump script, CHANGELOG, tagging and GitHub Actions use `setup_agent.iss` and version from `VERSION`.
