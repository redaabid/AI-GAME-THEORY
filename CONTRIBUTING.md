# Contributing

Start with the setup and test commands in [README.md](README.md). Discuss your
task with the team or create a GitHub issue before starting. The next milestone
is described in [docs/ROADMAP.md](docs/ROADMAP.md).

To add a model, create `agents/<name>.py` and compare it with `tournament.py`;
see [docs/COMMON_BASE.md](docs/COMMON_BASE.md).

1. Get the latest changes and create a branch:

   ```sh
   git switch main
   git pull --ff-only origin main
   git switch -c your-branch-name
   ```

2. Make your changes, run the checks, then commit and push:

   ```sh
   python -m unittest discover -s tests -v
   git add path/to/changed-file
   git commit -m "Describe your changes"
   git push -u origin your-branch-name
   ```

3. Open a pull request to `main` and ask a collaborator to review it.

Use a descriptive branch name, such as `reda/combat-simulator`. Keep each pull
request focused on one task, link its issue, and include the validation results.
Keep the baseline available so new strategies can be compared against it.

Add meaningful tests when changing protocol handling, game rules, or strategy
behavior. When an experiment changes results, record the maps, opponent versions,
starting sides, seeds, settings, and outcome counts so someone else can repeat it.

Keep local server files in `.local/`; they are ignored by Git. Commit code and
documentation with portable paths. Keep credentials, course archives, large
datasets, checkpoints, and generated logs out of commits.

Runtime search and game logic should be implemented by the team, following the
project brief's library restrictions. The instructor has permitted AI frameworks
for offline neural training. Document any future training dependencies separately
so colleagues can continue running the baseline without them.
