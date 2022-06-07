..
    Copyright 2022 Rafe Kaplan
    SPDX-License-Identifier: Apache-2.0

    Updated: 2022-06-06

Next Version
============
- Integration with readthe docs at https://conhead.readthedocs.io.

v0.4.0
======
- Provide alternate location for configuration file.

v0.3.0
======

- Can specify directory to command. Will process all files with
  matching template configuration.
- Support for new kinds of fields.
- Renamed YEAR field to YEARS.
- New DATE field.

v0.2.0
------

- ``.pre-commit-hooks.yaml`` so that ``conhead`` becomes
  a `pre-commit <https://pre-commit.com>`_ plugin.
- ``--delete`` switch that allows removal of existing headers.

v0.1.1
------

- Initial release
- Command line tool for adding or updating license
  headers for source files.
- Integration with `pyproject.toml` for configuration.
  Allow for varying license templates by file extension.
