# Frontend

## Purpose and Tools

`src/frontend/` contains the browser-facing React application.
The root `package.json` provides React, Mantine UI, Vite, TypeScript, and Oxlint tooling.

## Placement and Boundaries

Keep frontend source and frontend-specific assets within the established frontend structure.
Use Mantine for UI components and preserve the existing React and Vite setup.
Do not introduce another frontend framework or language without an approved project decision.

## Ownership and Acceptance

Ownership is not assigned by this orientation specification; establish it before making changes that could affect protected interfaces.
Frontend changes should pass the applicable commands documented in [validation.md](../validation.md).
