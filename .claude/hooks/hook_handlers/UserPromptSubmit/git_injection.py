#!/usr/bin/env python3
"""Git injection module for optimizing Claude Code responses with repository context."""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re


class GitInjector:
    """Injects valuable git information into Claude Code context."""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.git_dir = self.project_dir / ".git"
        
    def is_git_repo(self) -> bool:
        """Check if the current directory is a git repository."""
        return self.git_dir.exists()
    
    def run_git_command(self, cmd: List[str], check: bool = False) -> Optional[str]:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except subprocess.CalledProcessError:
            return None
        except Exception:
            return None
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current git branch name."""
        return self.run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    
    def get_main_branch(self) -> str:
        """Detect the main branch (main, master, or develop)."""
        for branch in ["main", "master", "develop"]:
            if self.run_git_command(["show-ref", f"refs/heads/{branch}"]):
                return branch
        return "main"  # Default fallback
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get comprehensive git status information."""
        status = {
            "branch": self.get_current_branch(),
            "main_branch": self.get_main_branch(),
            "status": "unknown",
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": [],
            "renamed": [],
            "conflicts": []
        }
        
        # Get porcelain status for parsing
        porcelain = self.run_git_command(["status", "--porcelain=v1"])
        if not porcelain:
            status["status"] = "clean"
            return status
        
        status["status"] = "dirty"
        
        for line in porcelain.split('\n'):
            if not line:
                continue
                
            status_code = line[:2]
            filepath = line[3:]
            
            # Parse status codes
            if status_code == "??":
                status["untracked"].append(filepath)
            elif status_code[0] in "AMDR":
                status["staged"].append(filepath)
            elif status_code[1] == "M":
                status["modified"].append(filepath)
            elif status_code[1] == "D":
                status["deleted"].append(filepath)
            elif status_code[0] == "R":
                status["renamed"].append(filepath)
            elif "U" in status_code:
                status["conflicts"].append(filepath)
        
        return status
    
    def get_recent_commits(self, limit: int = 10, days: int = 7) -> List[Dict[str, str]]:
        """Get recent commits with useful metadata."""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Format: hash|author|date|subject|files_changed|insertions|deletions
        log_format = "%H|%an|%ad|%s|"
        date_format = "--date=short"
        
        log_output = self.run_git_command([
            "log",
            f"--since={since_date}",
            f"--pretty=format:{log_format}",
            date_format,
            f"-{limit}",
            "--shortstat"
        ])
        
        if not log_output:
            return []
        
        commits = []
        current_commit = None
        
        for line in log_output.split('\n'):
            if not line:
                continue
                
            if '|' in line and not line.startswith(' '):
                # This is a commit line
                if current_commit:
                    commits.append(current_commit)
                
                parts = line.split('|')
                if len(parts) >= 4:
                    current_commit = {
                        "hash": parts[0][:7],  # Short hash
                        "author": parts[1],
                        "date": parts[2],
                        "subject": parts[3],
                        "stats": {"files": 0, "insertions": 0, "deletions": 0}
                    }
            elif line.strip() and current_commit:
                # This is a stats line
                stats_match = re.search(r'(\d+) file[s]? changed(?:, (\d+) insertion[s]?)?(?:, (\d+) deletion[s]?)?', line)
                if stats_match:
                    current_commit["stats"]["files"] = int(stats_match.group(1) or 0)
                    current_commit["stats"]["insertions"] = int(stats_match.group(2) or 0)
                    current_commit["stats"]["deletions"] = int(stats_match.group(3) or 0)
        
        if current_commit:
            commits.append(current_commit)
        
        return commits
    
    def get_file_change_summary(self) -> Dict[str, Any]:
        """Get summary of file changes and patterns."""
        summary = {
            "total_files": 0,
            "by_extension": {},
            "by_directory": {},
            "large_files": [],
            "recently_modified": []
        }
        
        # Get list of tracked files
        files_output = self.run_git_command(["ls-files"])
        if not files_output:
            return summary
        
        files = files_output.split('\n')
        summary["total_files"] = len(files)
        
        # Analyze by extension and directory
        for filepath in files:
            if not filepath:
                continue
                
            path = Path(filepath)
            
            # By extension
            ext = path.suffix or "no_extension"
            summary["by_extension"][ext] = summary["by_extension"].get(ext, 0) + 1
            
            # By top-level directory
            if path.parts:
                top_dir = path.parts[0]
                summary["by_directory"][top_dir] = summary["by_directory"].get(top_dir, 0) + 1
        
        # Get recently modified files (last 24 hours)
        recent_output = self.run_git_command([
            "log",
            "--since=24.hours.ago",
            "--name-only",
            "--pretty=format:"
        ])
        
        if recent_output:
            recent_files = [f for f in recent_output.split('\n') if f]
            summary["recently_modified"] = list(set(recent_files))[:10]  # Top 10 unique
        
        return summary
    
    def get_remote_info(self) -> Dict[str, Any]:
        """Get information about remote repositories."""
        remotes = {}
        
        remote_list = self.run_git_command(["remote", "-v"])
        if not remote_list:
            return remotes
        
        for line in remote_list.split('\n'):
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1]
                
                if name not in remotes:
                    remotes[name] = {"url": url}
                    
                    # Extract repo info from URL
                    if "github.com" in url:
                        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', url)
                        if match:
                            remotes[name]["owner"] = match.group(1)
                            remotes[name]["repo"] = match.group(2)
                            remotes[name]["platform"] = "github"
        
        return remotes
    
    def get_branch_info(self) -> Dict[str, Any]:
        """Get information about branches and their relationships."""
        info = {
            "current": self.get_current_branch(),
            "tracking": None,
            "ahead": 0,
            "behind": 0,
            "local_branches": [],
            "remote_branches": []
        }
        
        # Get tracking branch
        tracking = self.run_git_command(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        if tracking:
            info["tracking"] = tracking
            
            # Get ahead/behind counts
            counts = self.run_git_command(["rev-list", "--left-right", "--count", f"HEAD...{tracking}"])
            if counts:
                parts = counts.split()
                if len(parts) >= 2:
                    info["ahead"] = int(parts[0])
                    info["behind"] = int(parts[1])
        
        # Get local branches
        local_branches = self.run_git_command(["branch", "--format=%(refname:short)"])
        if local_branches:
            info["local_branches"] = local_branches.split('\n')
        
        # Get remote branches (limit to 10)
        remote_branches = self.run_git_command(["branch", "-r", "--format=%(refname:short)"])
        if remote_branches:
            info["remote_branches"] = remote_branches.split('\n')[:10]
        
        return info
    
    def inject_git_context(self) -> str:
        """Generate the git context injection string."""
        if not self.is_git_repo():
            return ""
        
        context_parts = []
        
        # Git status summary
        status = self.get_git_status()
        context_parts.append(f"gitStatus: This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.")
        context_parts.append(f"Current branch: {status['branch']}")
        context_parts.append(f"\nMain branch (you will usually use this for PRs): {status['main_branch']}\n")
        
        # Status details
        if status["status"] == "clean":
            context_parts.append("Status: Clean working directory")
        else:
            context_parts.append("Status:")
            
            # Group files by status
            if status["staged"]:
                for f in status["staged"][:10]:  # Limit to 10
                    context_parts.append(f"M {f}")
                if len(status["staged"]) > 10:
                    context_parts.append(f"... and {len(status['staged']) - 10} more staged files")
            
            if status["modified"]:
                for f in status["modified"][:10]:
                    context_parts.append(f" M {f}")
                if len(status["modified"]) > 10:
                    context_parts.append(f"... and {len(status['modified']) - 10} more modified files")
            
            if status["deleted"]:
                for f in status["deleted"][:5]:
                    context_parts.append(f" D {f}")
                if len(status["deleted"]) > 5:
                    context_parts.append(f"... and {len(status['deleted']) - 5} more deleted files")
            
            if status["untracked"]:
                for f in status["untracked"][:10]:
                    context_parts.append(f"?? {f}")
                if len(status["untracked"]) > 10:
                    context_parts.append(f"... and {len(status['untracked']) - 10} more untracked files")
        
        # Recent commits
        commits = self.get_recent_commits(limit=5, days=7)
        if commits:
            context_parts.append("\nRecent commits:")
            for commit in commits:
                stats = commit['stats']
                context_parts.append(
                    f"{commit['hash']} {commit['subject'][:60]}"
                )
        
        # Branch info
        branch_info = self.get_branch_info()
        if branch_info["tracking"]:
            if branch_info["ahead"] > 0 or branch_info["behind"] > 0:
                context_parts.append(
                    f"\nBranch status: {branch_info['ahead']} ahead, {branch_info['behind']} behind {branch_info['tracking']}"
                )
        
        # Remote info
        remotes = self.get_remote_info()
        if remotes and "origin" in remotes:
            origin = remotes["origin"]
            if "owner" in origin and "repo" in origin:
                context_parts.append(
                    f"\nRepository: {origin['owner']}/{origin['repo']}"
                )
        
        return "\n".join(context_parts)


def get_git_injection(project_dir: str) -> str:
    """Main entry point for git injection."""
    injector = GitInjector(project_dir)
    return injector.inject_git_context()


if __name__ == "__main__":
    # Test the injection
    import sys
    project_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(get_git_injection(project_dir))