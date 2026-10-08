# Contributing

Discuss your task with the team or create a GitHub issue before starting.

1. Get the latest changes and create a branch:

   ```sh
   git switch main
   git pull --ff-only origin main
   git switch -c your-branch-name
   ```

2. Make your changes, then commit and push:

   ```sh
   git add path/to/changed-file
   git commit -m "Describe your changes"
   git push -u origin your-branch-name
   ```

3. Open a pull request to `main` and ask a collaborator to review it.

Keep changes focused, use clear commit messages, and keep passwords and API keys out of the repository.
