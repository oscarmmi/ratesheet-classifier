# Planned portfolio app

This folder is a **new sibling repo** of `C:\xampp\htdocs\NewPortfolio`. Do not edit NewPortfolio except via artisan commands listed below.

## Agenda (production)

From `C:\xampp\htdocs\NewPortfolio`:

```
php artisan projects:planned
```

Require `"source": "production"`. Use the planned project id named in `PROMPT.md`.

Work **one pending task at a time**. After a slice:

```
php artisan projects:task-done {taskId}
```

You may rewrite the plan with `php artisan projects:plan-sync {id} path\to\tasks.json` if the list is wrong. The **spec** stays the contract.

When the app runs locally, git is committed, and GitHub exists:

```
php artisan projects:planned-done {id}
```

Marking `created` never inserts a live card on artechsano.com.

## Git / GitHub

- Path: `C:\xampp\htdocs\{slug}` (this folder)
- `git config user.name "Oscar Munoz"`
- `git config user.email "oscarxxi@gmail.com"`
- Public repo `https://github.com/oscarmmi/{slug}` on Oscar's account
- Push `main`. Do not leave the project only on disk.

English code. English README. No fake client logos. No Redis.
