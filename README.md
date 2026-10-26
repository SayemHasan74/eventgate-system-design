# EventGate Backend System Design

A documentation deliverable for the existing EventGate event management and ticketing project. No application code is changed.

## Diagrams

- [Open the ERD in Draw.io Viewer](https://app.diagrams.net/?lightbox=1&nav=1&title=EventGate%20ERD#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FSayemHasan74%2Feventgate-system-design%2F4e97d5e5eeb708c18c095c1123e91971f32037f5%2Fdiagrams%2Feventgate-erd.drawio)
- [Open the SDA workflow and architecture in Draw.io Viewer](https://app.diagrams.net/?lightbox=1&nav=1&title=EventGate%20Workflows#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FSayemHasan74%2Feventgate-system-design%2F4e97d5e5eeb708c18c095c1123e91971f32037f5%2Fdiagrams%2Feventgate-workflows.drawio)

Download the `.drawio` files in `diagrams/` to edit them in diagrams.net. The ERD has six named views, covers all 23 Prisma entities, and labels primary keys, foreign keys and unique constraints. Nullable foreign keys use `?`. Scalar pointers without a Prisma relation are not presented as enforced foreign keys. The document contains the complete foreign-key ledger, including links across views.

## Design basis

Backend source: [eventgate-api](https://github.com/SayemHasan74/eventgate-api), revision `f4f9396e83c317bc8b71e5a09762a1cd148ada9e`. API base `/api/v1`. The route inventory contains 109 API operations; it excludes browser BFF routes and infrastructure documentation endpoints. Request and response values in the document are illustrative design examples.

## Written document

The complete Word document is in `deliverables/`. It covers the project, roles, eight core features, workflows, architecture, database, API catalogue, ten detailed contracts, and failure handling. It can be uploaded to Google Drive and opened as Google Docs.

## Relationship audit

Run `python scripts/audit_relationships.py` after generating the diagrams. It independently reads declared foreign keys, nullability and single column uniqueness from the Prisma schema, then checks every Draw.io connector endpoint and visible cardinality. All 36 foreign keys are individually represented. Owner and check-in staff relations are separate; the payment replay relation uses an explicitly marked same-table alias. Labels `a : b` mean a parents per child and b children per parent.
