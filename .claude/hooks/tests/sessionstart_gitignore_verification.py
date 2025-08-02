#!/usr/bin/env python3
"""Verification script for SessionStart hook's .gitignore handling.

This script creates a temporary git repository with various files and .gitignore
patterns, then verifies that the SessionStart hook correctly excludes ignored files from
its operations.
"""

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Set

# Add parent directory to path to import SessionStart
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hook_handlers"))

try:
    from SessionStart import (
        gather_session_context,
        get_git_tracked_files,
        get_project_metadata,
        get_project_structure,
        get_readme_content,
        is_gitignored,
    )
except ImportError as e:
    print(f"Error importing SessionStart module: {e}", file=sys.stderr)
    sys.exit(1)


class GitIgnoreVerificationSuite:
    """Verification suite for .gitignore handling in SessionStart hook."""

    def __init__(self):
        self.temp_dir = None
        self.project_path = None

    def setup_verification_environment(self) -> None:
        """Create temporary directory with git initialization."""
        self.temp_dir = tempfile.mkdtemp(prefix="sessionstart_verify_")
        self.project_path = Path(self.temp_dir)

        # Initialize git repository
        subprocess.run(
            ["git", "init"],
            cwd=self.temp_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Verification User"],
            cwd=self.temp_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "verify@example.com"],
            cwd=self.temp_dir,
            check=True,
        )

        print(f"Created verification environment: {self.temp_dir}")

    def create_sample_files(self) -> Dict[str, Set[str]]:
        """Create sample files and directories with known patterns.

        Returns:
            Dictionary with 'tracked' and 'ignored' file sets
        """
        # Files that should be tracked
        tracked_files = {
            "README.md",
            "src/main.py",
            "src/utils.py",
            "spec/main_spec.py",
            "requirements.txt",
            "package.json",
            "docs/guide.md",
            "config/settings.yaml",
        }

        # Files that should be ignored
        ignored_files = {
            ".env",
            ".env.local",
            "node_modules/package/index.js",
            "node_modules/another/lib.js",
            "__pycache__/main.cpython-39.pyc",
            "__pycache__/utils.cpython-39.pyc",
            "dist/bundle.js",
            "dist/assets/style.css",
            "build/output.log",
            ".DS_Store",
            "temp_file.tmp",
            "logs/debug.log",
            "logs/error.log",
            ".vscode/settings.json",
            ".idea/workspace.xml",
            "coverage/.coverage",
            "*.bak",
        }

        # Create all directories first
        all_files = tracked_files | ignored_files
        for file_path in all_files:
            if file_path.endswith("*"):  # Skip glob patterns
                continue
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file with some content
            if file_path.endswith(".md"):
                content = f"# {file_path}\n\nThis is a sample file for {file_path}"
            elif file_path.endswith(".py"):
                content = f'"""Sample file: {file_path}"""\n\ndef main():\n    pass'
            elif file_path.endswith(".json"):
                content = f'{{"name": "sample", "file": "{file_path}"}}'
            elif file_path.endswith(".js"):
                content = f'// Sample file: {file_path}\nconsole.log("sample");'
            else:
                content = f"Sample content for {file_path}"

            full_path.write_text(content)

        # Create some .bak files for glob pattern verification
        (self.project_path / "backup.bak").write_text("backup content")
        (self.project_path / "old_config.bak").write_text("old config")

        return {"tracked": tracked_files, "ignored": ignored_files}

    def create_gitignore(self) -> None:
        """Create .gitignore file with sample patterns."""
        gitignore_content = """# Environment files
.env
.env.*

# Dependencies
node_modules/

# Python cache
__pycache__/
*.pyc

# Build outputs
dist/
build/

# OS files
.DS_Store

# Temporary files
*.tmp
*.bak

# Logs
logs/

# IDE files
.vscode/
.idea/

# Coverage
coverage/
"""

        gitignore_path = self.project_path / ".gitignore"
        gitignore_path.write_text(gitignore_content)
        print("Created .gitignore with sample patterns")

    def commit_tracked_files(self, tracked_files: Set[str]) -> None:
        """Add and commit only the tracked files to git."""
        # Add .gitignore first
        subprocess.run(["git", "add", ".gitignore"], cwd=self.temp_dir, check=True)

        # Add tracked files
        for file_path in tracked_files:
            try:
                subprocess.run(
                    ["git", "add", file_path],
                    cwd=self.temp_dir,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                print(f"Warning: Could not add {file_path} (may not exist)")

        # Commit all tracked files
        subprocess.run(
            ["git", "commit", "-m", "Initial commit with tracked files"],
            cwd=self.temp_dir,
            check=True,
            capture_output=True,
        )
        print("Committed tracked files to git")

    async def verify_git_tracked_files(self, expected_tracked: Set[str]) -> bool:
        """Verify that get_git_tracked_files() returns only tracked files."""
        print("\n=== Verifying get_git_tracked_files() ===")

        tracked_files = await get_git_tracked_files(self.temp_dir)
        tracked_set = set(tracked_files)

        # Add .gitignore to expected since we track it
        expected_with_gitignore = expected_tracked | {".gitignore"}

        print(f"Expected tracked files: {len(expected_with_gitignore)}")
        print(f"Actual tracked files: {len(tracked_set)}")

        # Check for missing files
        missing = expected_with_gitignore - tracked_set
        if missing:
            print(f"Missing tracked files: {missing}")

        # Check for unexpected files
        unexpected = tracked_set - expected_with_gitignore
        if unexpected:
            print(f"Unexpected tracked files: {unexpected}")

        success = missing == set() and unexpected == set()
        print(
            "✅ PASS: git tracked files correct"
            if success
            else "❌ FAIL: git tracked files incorrect"
        )
        return success

    async def verify_is_gitignored(
        self, tracked_files: Set[str], ignored_files: Set[str]
    ) -> bool:
        """Verify that is_gitignored() correctly identifies ignored files."""
        print("\n=== Verifying is_gitignored() ===")

        success = True

        # Verify tracked files should NOT be ignored
        print("Verifying tracked files (should NOT be ignored):")
        for file_path in tracked_files:
            if (self.project_path / file_path).exists():
                ignored = await is_gitignored(file_path, self.temp_dir)
                if ignored:
                    print(f"❌ FAIL: {file_path} should NOT be ignored but is")
                    success = False
                else:
                    print(f"✅ PASS: {file_path} correctly not ignored")

        # Verify ignored files should BE ignored
        print("\nVerifying ignored files (should BE ignored):")
        for file_path in ignored_files:
            if file_path.endswith("*"):  # Skip glob patterns for direct verification
                continue
            if (self.project_path / file_path).exists():
                ignored = await is_gitignored(file_path, self.temp_dir)
                if not ignored:
                    print(f"❌ FAIL: {file_path} should be ignored but is not")
                    success = False
                else:
                    print(f"✅ PASS: {file_path} correctly ignored")

        # Verify glob patterns with actual files
        print("\nVerifying glob patterns:")
        glob_files = ["backup.bak", "old_config.bak"]
        for file_path in glob_files:
            ignored = await is_gitignored(file_path, self.temp_dir)
            if not ignored:
                print(
                    f"❌ FAIL: {file_path} should match *.bak pattern but is not ignored"
                )
                success = False
            else:
                print(f"✅ PASS: {file_path} correctly matches *.bak pattern")

        print(
            "✅ PASS: gitignore detection correct"
            if success
            else "❌ FAIL: gitignore detection has errors"
        )
        return success

    async def verify_project_structure(self, expected_tracked: Set[str]) -> bool:
        """Verify that get_project_structure() only includes directories with tracked
        files."""
        print("\n=== Verifying get_project_structure() ===")

        structure = await get_project_structure(self.temp_dir)
        structure_dirs = set(structure.split("\n")) if structure else set()

        # Expected directories are those that contain tracked files
        expected_dirs = set()
        for file_path in expected_tracked:
            path_parts = Path(file_path).parts
            for depth in range(1, min(len(path_parts), 4)):
                dir_path = "/".join(path_parts[:depth])
                expected_dirs.add(dir_path)

        print(f"Expected directories: {expected_dirs}")
        print(f"Actual directories: {structure_dirs}")

        # Remove empty strings
        structure_dirs.discard("")

        # Check if structure only contains directories with tracked files
        success = (
            structure_dirs <= expected_dirs
        )  # structure_dirs should be subset of expected

        if not success:
            unexpected = structure_dirs - expected_dirs
            print(f"Unexpected directories in structure: {unexpected}")

        print(
            "✅ PASS: project structure respects gitignore"
            if success
            else "❌ FAIL: project structure includes ignored directories"
        )
        return success

    async def verify_readme_content(self) -> bool:
        """Verify that get_readme_content() respects .gitignore."""
        print("\n=== Verifying get_readme_content() ===")

        # README.md should be tracked and readable
        readme_content = await get_readme_content(self.temp_dir)

        success = bool(readme_content) and "README.md" in readme_content
        print(
            "✅ PASS: README content loaded"
            if success
            else "❌ FAIL: README content not loaded"
        )

        # Verify with ignored README (create one in ignored directory)
        ignored_readme_dir = self.project_path / "node_modules"
        ignored_readme_dir.mkdir(exist_ok=True)
        ignored_readme = ignored_readme_dir / "README.md"
        ignored_readme.write_text("# Ignored README\nThis should be ignored")

        # Should still get the tracked README, not the ignored one
        readme_content_after = await get_readme_content(self.temp_dir)
        success_after = readme_content_after == readme_content

        print(
            "✅ PASS: Ignored README not interfering"
            if success_after
            else "❌ FAIL: Ignored README interfering"
        )

        return success and success_after

    async def verify_project_metadata(self) -> bool:
        """Verify that get_project_metadata() respects .gitignore."""
        print("\n=== Verifying get_project_metadata() ===")

        metadata = await get_project_metadata(self.temp_dir)

        # Should find package.json and requirements.txt (tracked)
        expected_metadata = {"npm", "python-pip"}
        actual_metadata = set(metadata.keys())

        print(f"Expected metadata types: {expected_metadata}")
        print(f"Actual metadata types: {actual_metadata}")

        success = expected_metadata <= actual_metadata

        # Create ignored metadata file
        ignored_dir = self.project_path / "build"
        ignored_dir.mkdir(exist_ok=True)
        ignored_package = ignored_dir / "package.json"
        ignored_package.write_text('{"name": "ignored-package"}')

        # Should not pick up ignored metadata
        metadata_after = await get_project_metadata(self.temp_dir)
        success_after = len(metadata_after) == len(metadata)

        print(
            "✅ PASS: Project metadata respects gitignore"
            if (success and success_after)
            else "❌ FAIL: Project metadata issues"
        )

        return success and success_after

    async def verify_full_session_context(self) -> bool:
        """Verify the full gather_session_context() function."""
        print("\n=== Verifying gather_session_context() ===")

        context = await gather_session_context(self.temp_dir)

        # Verify context structure
        required_keys = {
            "files",
            "structure",
            "readme",
            "commits",
            "status",
            "metadata",
            "file_types",
            "execution_time",
            "total_files",
        }

        missing_keys = required_keys - set(context.keys())
        if missing_keys:
            print(f"❌ FAIL: Missing context keys: {missing_keys}")
            return False

        # Verify files list contains only tracked files
        context_files = set(context["files"])
        expected_files = {
            "README.md",
            "src/main.py",
            "src/utils.py",
            "spec/main_spec.py",
            "requirements.txt",
            "package.json",
            "docs/guide.md",
            "config/settings.yaml",
            ".gitignore",
        }

        unexpected_files = context_files - expected_files
        if unexpected_files:
            print(f"❌ FAIL: Context contains ignored files: {unexpected_files}")
            return False

        # Verify file types summary
        file_types = context["file_types"]
        expected_extensions = {".md", ".py", ".txt", ".json", ".yaml"}
        actual_extensions = set(file_types.keys())

        if not expected_extensions <= actual_extensions:
            print("❌ FAIL: Missing expected file extensions in summary")
            return False

        print(f"Context execution time: {context['execution_time']:.3f}s")
        print(f"Total files in context: {context['total_files']}")
        print(f"File types: {file_types}")

        print("✅ PASS: Full session context respects gitignore")
        return True

    def cleanup(self) -> None:
        """Clean up verification environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up verification environment: {self.temp_dir}")

    async def run_all_verifications(self) -> bool:
        """Run all verifications and return overall success."""
        print("🧪 Starting SessionStart .gitignore Verification")
        print("=" * 50)

        try:
            # Setup
            self.setup_verification_environment()
            file_sets = self.create_sample_files()
            self.create_gitignore()
            self.commit_tracked_files(file_sets["tracked"])

            # Run verifications
            results = []
            results.append(await self.verify_git_tracked_files(file_sets["tracked"]))
            results.append(
                await self.verify_is_gitignored(
                    file_sets["tracked"], file_sets["ignored"]
                )
            )
            results.append(await self.verify_project_structure(file_sets["tracked"]))
            results.append(await self.verify_readme_content())
            results.append(await self.verify_project_metadata())
            results.append(await self.verify_full_session_context())

            # Summary
            print(f"\n{'=' * 50}")
            passed = sum(results)
            total = len(results)

            if passed == total:
                print(f"🎉 ALL VERIFICATIONS PASSED ({passed}/{total})")
                print("✅ SessionStart hook properly respects .gitignore rules")
                return True
            else:
                print(f"❌ SOME VERIFICATIONS FAILED ({passed}/{total})")
                print("⚠️  SessionStart hook has .gitignore issues")
                return False

        except Exception as e:
            print(f"💥 VERIFICATION SUITE ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.cleanup()


def main():
    """Main verification runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        print("\nUsage: python sessionstart_gitignore_verification.py [--verbose]")
        print("\nThis script verifies that the SessionStart hook correctly:")
        print("• Only processes git-tracked files")
        print("• Respects .gitignore patterns")
        print("• Excludes ignored files from all operations")
        print("• Handles glob patterns correctly")
        return

    # Set debug mode if verbose
    if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        os.environ["DEBUG_HOOKS"] = "1"

    # Run the verification suite
    verification_suite = GitIgnoreVerificationSuite()
    success = asyncio.run(verification_suite.run_all_verifications())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
