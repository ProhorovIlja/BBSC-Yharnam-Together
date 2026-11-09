# SPDX-License-Identifier: GPL-2.0-or-later
"""B20: verify release-only heavy CI and GHCR publication rules. No deployment."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/deploy.yml"


class HostedServerReleaseScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def job_section(self, name):
        m = re.search(r"(?m)^  " + re.escape(name) + r":\s*$", self.source)
        self.assertIsNotNone(m, "missing job " + name)
        after = re.search(r"(?m)^  [a-z0-9_-]+:\s*$", self.source[m.end():])
        return self.source[m.end():m.end()+after.start()] if after else self.source[m.end():]

    def test_every_heavy_job_scoped_to_release_target_prs_or_manual(self):
        expected = ("github.event_name != 'pull_request' || "
                    "github.base_ref == 'main' || github.base_ref == 'hosted-server'")
        for name in ("chart", "terraform", "image"):
            with self.subTest(job=name):
                section = self.job_section(name)
                self.assertRegex(section, r"(?m)^    if: " + re.escape(expected) + r"$")
                self.assertIn("runs-on: ubuntu-latest", section)
        cases = [
            ("pull_request", "experiment/ultimate-batch-19", False),
            ("pull_request", "feature/server-private-world-sync-health-v1", False),
            ("pull_request", "main", True),
            ("pull_request", "hosted-server", True),
            ("push", "", True),
            ("workflow_dispatch", "", True),
        ]
        for event, base, expected_allowed in cases:
            with self.subTest(event=event, base=base):
                allowed = event != "pull_request" or base in {"main", "hosted-server"}
                self.assertEqual(allowed, expected_allowed)

    def test_publish_requires_push_to_named_release_branch(self):
        expected = ("${{ github.event_name == 'push' && "
                    "(github.ref == 'refs/heads/main' || github.ref == 'refs/heads/hosted-server') }}")
        image = self.job_section("image")
        self.assertIn("        if: " + expected, image)
        self.assertEqual(image.count("          push: " + expected), 2)
        self.assertIn("          load: ${{ github.event_name != 'push' }}", image)
        for event, branch, want in [
            ("pull_request", "main", False),
            ("pull_request", "hosted-server", False),
            ("workflow_dispatch", "main", False),
            ("workflow_dispatch", "experiment/ultimate-batch-20", False),
            ("push", "experiment/ultimate-batch-20", False),
            ("push", "main", True),
            ("push", "hosted-server", True),
        ]:
            with self.subTest(event=event, branch=branch):
                actual = event == "push" and branch in {"main", "hosted-server"}
                self.assertEqual(actual, want)

    def test_original_helm_terraform_smoke_and_manual_gates_retained(self):
        s = self.source
        for token in (
            "  workflow_dispatch:",
            "    branches: [main, hosted-server]",
            "helm lint",
            "terraform fmt -recursive -check -diff",
            "terraform -chdir=root validate",
            "needs: [chart, terraform]",
            "docker/build-push-action@v6",
            "docker exec smoke shadnet --admin stats",
            "docker rm -f smoke",
            "cache-to: type=gha,mode=max,scope=shadnet",
        ):
            self.assertIn(token, s, token)
        self.assertIn("server/**", s)
        self.assertNotIn("if: github.event_name != 'pull_request'\n        with:", s)


if __name__ == "__main__":
    unittest.main()
