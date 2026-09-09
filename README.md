# Project Template

A multi-language project template for building applications with:

* **Frontend:** React + TypeScript + Mantine
* **Business:** Python
* **DevTools:** Kotlin + Jetpack Compose + Composables UI

The frontend uses **Vite** and TypeScript, while the business uses **uv** and **pytest**. 
The template also includes the supporting configuration and tooling needed to develop and test each part of the project.

> [!WARNING]
> **Use kebab-case for your repository name.**
>
> Name your project using lowercase letters, numbers, and hyphens:
>
> * `my-project` ✓
> * `my_project` ✗
> * `myProject` ✗
>
> Some project tooling, particularly the Node.js tooling, expects the project name to use kebab-case.

## Getting Started

### 1. Create your project

Use this repository as a template or clone it into a new repository.

**Use a kebab-case name for the new project.**

For example:

```text
my-project
```

### 2. Initialize the project

Run:

```text
init
```

`init` bootstraps the project and places the project's scripts on the path.

On the first run, it will ask for some values for the env to be set, just press `Enter` on all of them. We will come back to configuring them later.

### 3. Rename the project

Run:

```text
rename_project my-project
```

Replace `my-project` with the name you chose for your repository.

This replaces the template's `project-template` and `project_template` names throughout the project and renames the corresponding directories.

### 4. Verify the project

Optionally run the project to verify that everything was initialized correctly.

```
run --source frontend
run --source business
run --source devtools
```

### 5. Pull the vault

Run:

```text
vault pull
```

This extracts the template's documentation into `docs/vault/`.

The template vault contains documentation files that are useful while setting up the project.

### 6. Generate a new vault key

Once the template vault has been pulled, generate a new key:

```text
vault key
```

Copy the generated key into `.env` as `VAULT_KEY`.

The new project should use its own vault key rather than continuing to use the template's key.

## After Setup

The project is now ready for development.

The `rename_project` script is intended as a one-off template conversion tool. Once the project has been renamed successfully, it is no longer useful and may be deleted.

The remaining project utilities can be used as needed during development.

## Extra Notes on Vault

Extract the vault to learn more!

[Vault Notes](docs/vault/README.md)
