# immunisation-fhir-api Terraform

## Setup for local dev

Add your workspace name to the env file. This is usually your shortcode.

```shell
echo environment=your-shortcode >> .env
make init
make workspace
make apply
```

See the Makefile for other commands.

If you want to apply Terraform to a workspace created by a PR you can set the above environment to the PR number.
E.g. `pr-57`. You can use this to test out changes when tests fail in CI.
