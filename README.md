# WB Mock API Server

This repository contains the mock Wildberries API data generator used by the WB pipeline project.

## Server role

Server 1 generates realistic mock JSON payloads and exposes them through nginx from:

/var/www/html

Server 2 consumes these JSON files, loads them into PostgreSQL, and transforms them through dbt.

## Main scripts

- scripts/generate_realistic_mock_json.py
- scripts/link_mock_json_entities.py
- scripts/fix_mock_entity_links_from_catalog.py

## WB OpenAPI specs

The WB OpenAPI YAML specs are stored in:

specs/

## Generated files

Generated JSON files are not stored in git. They are generated on the server and published into:

/var/www/html

## Nginx

The current nginx site config template is stored in:

config/nginx/default.conf
