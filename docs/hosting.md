# Hosted portfolio demo

The Render Blueprint runs the lightweight Docker image with the bundled synthetic dataset. Visitors can search immediately as Ines, the general-staff persona. The server still filters permissions before ranking and rejects identity overrides. Generated answers are disabled.

## Deploy from GitHub

1. Merge the reliability improvements and hosted-demo pull requests into main.
2. Sign in to [Render](https://dashboard.render.com/) using GitHub.
3. Choose **New → Blueprint** and connect **NehaPrajwal1/vaultsearch**.
4. Select **main** and use the root `render.yaml`.
5. Confirm the **Free** plan and create the Blueprint.
6. Wait for the service to become Live, then open its assigned HTTPS URL.

Render generates the internal deployment token automatically. Visitors never need this token. Public mode is opt-in and requires the exact bundled synthetic corpus and identity directory; replacing either causes startup to fail. Private installations keep their existing bearer-token requirement.

## Visitor walkthrough

- Search **paid time off** and expand a source excerpt.
- Search **Q3 infrastructure budget** to see permitted results for general staff.
- Open **How it works** for the architecture explanation.
- Link the assigned HTTPS URL from your portfolio and repository.

No model downloads, AWS account, database, persistent disk or laptop runtime is required. Render supplies the listening port through `PORT`. Automatic deployments wait for GitHub checks to pass.

Free instances sleep after 15 minutes without traffic; a first visit can take about a minute. Their filesystem is ephemeral, which suits this bundled read-only dataset. See [Render's free service documentation](https://render.com/docs/free) for current limits.

Turning off public mode restores the operator-token connection flow. Keep public hosting on the shipped synthetic dataset.
