from ast import parse
from ctypes import util
import os
import shutil, tempfile

from git import GitCommandError
import git
import git.cmd
from gitdb.util import to_bin_sha
from vc.versioncontrol_interface import *
import vc.apgit.utility as utility
import vc.apgit.lfs as lfs

import gc

def _map_op_code(op_code: int) -> str:
    if op_code == 32:
        return "downloading"
    if op_code == 256:
        return "updating"
    if op_code == 4:
        return "counting"
    if op_code == 64:
        return "resolving"
    if op_code == 16:
        return "writing"
    if op_code == 8:
        return "compressing"
    return str(op_code)

def _parse_lfs_status(progress, line: str):
    try:
        import re
        
        def report_lfs_progress(text_identifier, op_code):
            count_match = re.search("\(\d+\/\d+\)", line)
            if count_match:
                cur_count = re.search("\d+\/", count_match.group()).group()[:-1]
                max_count = re.search("\d+\)", count_match.group()).group()[:-1]
                progress_text = line.replace(text_identifier, "").strip()
                progress.update(_map_op_code(op_code), int(cur_count), int(max_count), progress_text)

        # Filtering content: 100% (23/23), 59.33 MiB | 8.63 MiB/s
        if "Filtering content:" in line:     
            report_lfs_progress("Filtering content: ", 32)
        
        # Uploading LFS objects: 100% (1/1), 3.6 KB | 0 B/s, done.
        if "Uploading LFS objects:" in line:
            report_lfs_progress("Uploading LFS objects: ", 16)

        # Downloading LFS objects: 100% (1/1), 3.6 KB | 0 B/s, done.
        if "Downloading LFS objects:" in line:
            report_lfs_progress("Downloading LFS objects: ", 32)

    except Exception as e:
        print(e)
    
class _InternalProgress(git.RemoteProgress):
    def __init__(self, progress) -> None:
        super().__init__()
        self.progress = progress

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.progress.update(_map_op_code(op_code), cur_count, max_count, message if len(message) > 0 else None)

    def line_dropped(self, line: str) -> None:
        _parse_lfs_status(self, line)
        return super().line_dropped(line)

    def canceled(self):
        return self.progress.ap_progress.canceled
class GitRepository(VCRepository):
    repo: git.Repo = None

    def __del__(self) -> None:
        # GitPython tends to leak memory / keeps git.exe processes dangling
        if self.repo:
            del self.repo 
        
        gc.collect()
        
        # print("\n\nDELETING git repo. If this message does not show up we are leaking memory\n\n")

    @staticmethod
    def is_repo(path: str) -> bool:
        return os.path.exists(os.path.join(path, ".git"))

    @staticmethod
    def is_authenticated(url: str) -> bool: 
        try:
            import subprocess
            utility.run_git_command([utility.get_git_cmd_path(), "ls-remote", url], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except Exception as e:
            return False
        return True

    @staticmethod
    def authenticate(url: str, username: str, password: str):
        from subprocess import run
        from urllib.parse import urlparse
        parsedurl = urlparse(url)
        host = parsedurl.hostname
        protocol = parsedurl.scheme
        
        cmd = [utility.get_gcm_path(), "store"]
        p = run(cmd, input=f"host={host}\nprotocol={protocol}\nusername={username}\npassword={password}", text=True)
        if p.returncode != 0:
            raise GitCommandError(cmd, p.returncode, p.stderr, p.stdout)

    @classmethod
    def create(cls, path: str):
        utility.run_git_command([utility.get_git_cmd_path(), "init", "-b", "main"], cwd=path)
        return GitRepository.load(path)

    @classmethod
    def clone(cls, remote_url: str, local_path: str, progress: Optional[Progress] = None):
        env = GitRepository.get_git_environment()
        try:
            if progress is not None:
                git.Repo.clone_from(remote_url, local_path,  progress = _InternalProgress(progress), env=env)
            else:
                git.Repo.clone_from(remote_url, local_path, env=env)
        except GitCommandError as e:
            print("GitError: ", str(e.status), str(e.stderr), str(e.stdout), str(e))
            raise e

        return GitRepository.load(local_path)

    @classmethod
    def load(cls, path: str):
        repo = cls()
        repo.repo = git.Repo(path, search_parent_directories=True)
        repo._setup_environment()
        return repo

    @staticmethod
    def get_git_environment():
        def add_config_env(config, key, value, config_count):
            config[f"GIT_CONFIG_KEY_{config_count}"] = key
            config[f"GIT_CONFIG_VALUE_{config_count}"] = value.replace("\\","/")
            config["GIT_CONFIG_COUNT"] = str(config_count + 1)

        env = {
            "GIT_EXEC_PATH": utility.get_git_exec_path().replace("\\","/"),
            "GIT_LFS_FORCE_PROGRESS": "1" 
        }

        add_config_env(env, "credential.helper", utility.get_gcm_path(), 0)
        add_config_env(env, "credential.https://dev.azure.com.usehttppath", "1", 1)
        return env

    def _setup_environment(self):
        self.repo.git.update_environment(**GitRepository.get_git_environment()) 

    def _has_upstream(self):
        try:
            self.get_remote_change_id()
            return True
        except:
            return False

    def _set_upstream(self, remote, branch):
        self.repo.git.branch("-u", remote, branch)

    def push(self, progress: Optional[Progress] = None) -> UpdateState:
        branch = self._get_current_branch()
        remote = self._get_default_remote(branch)
        if remote is None: remote = "origin"

        kwargs = {}
        if not self._has_upstream():
            kwargs["set-upstream"] = True

        try:
            current_env = os.environ.copy()
            current_env.update(GitRepository.get_git_environment())
            progress_wrapper = None if not progress else _InternalProgress(progress)
            lfs.lfs_push(self.get_root_path(), remote, branch, progress_wrapper, current_env)
            if progress_wrapper.canceled(): return UpdateState.CANCEL
            state = UpdateState.OK
            for info in self.repo.remote(remote).push(refspec=branch, progress = progress_wrapper, **kwargs):
                if info.flags & git.PushInfo.ERROR:
                    state = UpdateState.ERROR
            return state
        except Exception as e:
            raise e

    def fetch(self, progress: Optional[Progress] = None) -> UpdateState:
        branch = self._get_current_branch()
        remote = self._get_default_remote(branch)
        if remote is None: remote = "origin"

        state = UpdateState.OK
        if progress is not None:
            for info in self.repo.remote(remote).fetch(progress = _InternalProgress(progress)):
                if info.flags & git.FetchInfo.ERROR:
                    state = UpdateState.ERROR
        else: 
            for info in self.repo.remote(remote).fetch():
                if info.flags & git.FetchInfo.ERROR:
                    state = UpdateState.ERROR

        return state

    def update(self, progress: Optional[Progress] = None, rebase = True) -> UpdateState:
        branch = self._get_current_branch()
        remote = self._get_default_remote(branch)
        if remote is None: return UpdateState.NO_REMOTE

        state = UpdateState.OK
        try:
            current_env = os.environ.copy()
            current_env.update(GitRepository.get_git_environment())
            progress_wrapper = None if not progress else _InternalProgress(progress)
            lfs.lfs_fetch(self.get_root_path(), remote, progress_wrapper, current_env)
            if progress_wrapper.canceled(): return UpdateState.CANCEL
            for info in self.repo.remote(remote).pull(progress = progress_wrapper, rebase = rebase, refspec=branch):
                if info.flags & git.FetchInfo.ERROR:
                    state = UpdateState.ERROR

        except Exception as e:
            if self.has_conflicts():
                return UpdateState.CONFLICT
            raise e

        return state

    def revert_changelist(self, changelist_id: str):
        self.repo.git.revert(changelist_id, "-Xtheirs", "-n")

    def restore_changelist(self, changelist_id: str):
        self.repo.git.restore(".", "--ours", "--overlay", "--source", changelist_id)

    def restore_files(self, files: list[str]):
        self.repo.git.checkout("--", *files)

    def clean(self):
        self.repo.git.clean("-fd")

    def restore_all_files(self):
        self.repo.git.checkout(".")

    def switch_branch(self, branch_name: str):
        split = branch_name.split("/")
        if len(split) > 1:
            try:
                remote = self.repo.remote(split[0])
                if remote:
                    branch_name = "/".join(split[1:])
            except Exception as e:
                print(str(e))
                pass
        
        self.repo.git.switch(branch_name)

    def create_branch(self, branch_name: str):
        self.repo.git.switch("-c", branch_name)

    def stash(self):
        self.repo.git.stash()

    def pop_stash(self):
        self.repo.git.stash("pop")

    def get_remote_url(self):
        if self.has_remote():
            branch = self._get_current_branch()
            remote = self._get_default_remote(branch)
            urls = self.repo.remote(remote).urls
            return next(urls)
            
        return None

    def is_unborn(self):
        try:
            self.repo.rev_parse("HEAD")
        except:
            return True
        return False

    def _is_sha1(self):
        format = self.repo.git.rev_parse("--show-object-format")
        return format == "sha1"

    def _get_empty_tree_id(self):
        # Magic number, can be retrieved with "git hash-object -t tree /dev/null"
        if self._is_sha1():
            return "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        else:
            return "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321"

    def has_pending_changes(self, include_untracked):
        if include_untracked: return self.get_pending_changes().size() > 0 or self.get_pending_changes(True).size() > 0
        diff = self.repo.index.diff(None) 
        return len(diff) > 0 or self.get_pending_changes(True).size() > 0

    def _get_untracked_files(self, *args, **kwargs):
        from git.util import finalize_process
        import sys
        defenc = sys.getfilesystemencoding()

        # make sure we get all files, not only untracked directories
        proc = self.repo.git.status(*args,
                               porcelain=True,
                               untracked_files=True,
                               as_process=True,
                               **kwargs)
        # Untracked files prefix in porcelain mode
        prefix = "?? "
        untracked_files = []
        for line in proc.stdout:
            line_decoded = line.decode(defenc)
            if not line_decoded.startswith(prefix):
                continue
            filename = line_decoded[len(prefix):].rstrip('\n')
            
            # Special characters are escaped
            if filename[0] == filename[-1] == '"':
                filename = line_decoded[len(prefix):].rstrip('\n')
                filename = filename[1:-1].replace("\\","")
                
            untracked_files.append(filename)
        finalize_process(proc)
        return untracked_files

    def get_pending_changes(self, staged: bool = False) -> Changes:
        changes = Changes()
        try:
            if staged:
                if not self.is_unborn():
                    diff = self.repo.head.commit.diff()
                else:
                    diff = self.repo.index.diff(self._get_empty_tree_id())
            else:
                diff = self.repo.index.diff(None) 
            
            self._get_file_changes(diff, changes)
            
            if not staged:
                for untracked_file in self._get_untracked_files("-uall"):
                    changes.new_files.append(Change(path = untracked_file)) 
        except ValueError as e:
            print(e)
            pass

        return changes

    def get_changes_for_changelist(self, id: str) -> Changes:
        changes = Changes()
        try:
            commit = self.repo.commit(id)
            if len(commit.parents) >= 1:
                parent = commit.parents[0]
                diff = parent.diff(commit)
            else:
                empty_tree = git.Tree(self.repo, to_bin_sha(self._get_empty_tree_id()))
                diff = empty_tree.diff(commit)

            self._get_file_changes(diff, changes)

        except Exception as e:
            print (e)

        return changes

    def _write_pathspec_file(self, paths, file):
        with open(file, "w") as f:
            f.writelines("{}\n".format(x) for x in paths)

    def stage_all_files(self):
        self.repo.git.add(".")

    def unstage_all_files(self):
        self.repo.git.restore("--staged", ".")

    def stage_files(self, paths: list[str]):
        if len(paths) > 20:
            with tempfile.TemporaryDirectory() as dirpath:
                pathspec = os.path.join(dirpath, "spec")
                self._write_pathspec_file(paths, pathspec)
                self.repo.git.add(pathspec_from_file=pathspec)        
        else:
            self.repo.git.add(*paths)

    def unstage_files(self, paths: list[str]):
        if len(paths) > 20:
            with tempfile.TemporaryDirectory() as dirpath:
                pathspec = os.path.join(dirpath, "spec")
                self._write_pathspec_file(paths, pathspec)
                self.repo.git.restore("--staged", pathspec_from_file=pathspec)        
        else:
            self.repo.git.restore("--staged", *paths)

    def sync_staged_files(self, paths: list[str]):
        if not self.is_unborn():
            staged_files = self.repo.git.diff("--name-only", "--staged").splitlines()
            if len(staged_files) > 0:
                self.repo.git.restore("--staged", *staged_files)
        self.stage_files(paths)

    def remove_files(self, paths: list[str]):
        if len(paths) > 20:
            with tempfile.TemporaryDirectory() as dirpath:
                pathspec = os.path.join(dirpath, "spec")
                self._write_pathspec_file(paths, pathspec)
                self.repo.git.rm(pathspec_from_file=pathspec)        
        else:
            self.repo.git.rm(*paths)

    def commit(self, message: str):
        args = [utility.get_git_cmd_path(), "commit", "-m", message]
        gpg = shutil.which("gpg")
        if not gpg:
            args.insert(1, "commit.gpgsign=false")
            args.insert(1, "-c") 
            
        utility.run_git_command(args, cwd=self.get_root_path())

    def get_git_dir(self):
        return self.repo.git_dir

    def get_root_path(self):
        return self.repo.working_dir

    def track_lfs(self, extensions: list[str]):
        patterns = ["*" + ext for ext in extensions]
        self.repo.git.lfs("track", patterns)

    def track_lfs_files(self, paths: list[str]):
        repo_dir = self.get_root_path()
        rel_paths = [os.path.relpath(path, repo_dir) for path in paths]
        self.repo.git.lfs("track", rel_paths)

    def get_deleted_files(self):
        unstaged_files = []
        staged_files = []
        status_lines = self.repo.git.status(porcelain=True).splitlines()
        for status in status_lines:
            split = status.split()
            if len(split) > 1:
                marker = split[0]
                marker_length = len(marker)
                if marker_length == 0: 
                    continue

                file = " ".join(split[1:]).replace("\"", "")
                if marker[0] == "D":
                    unstaged_files.append(file)

                if marker_length > 1 and marker[1] == "D":
                    staged_files.append(file)
                
        return unstaged_files, staged_files

    def get_conflicts(self):
        def is_conflict(status_ids: str):
            if len(status_ids) <= 1: return False
            if "U" in status_ids: return True
            return status_ids in ["DD", "AA"]

        conflicts = []
        status_lines = self.repo.git.status(porcelain=True).splitlines()
        for status in status_lines:
            split = status.split()
            if len(split) > 1:
                status_ids = split[0]
                if is_conflict(status_ids):
                    conflicts.append(" ".join(split[1:]).replace("\"", ""))    

        return conflicts

    def has_conflicts(self):
        return len(self.get_conflicts()) > 0

    def is_rebasing(self):
        repodir = self._get_repo_internal_dir()
        rebase_dirs = ["rebase-merge", "rebase-apply"]
        for dir in rebase_dirs:
            if os.path.exists(os.path.join(repodir, dir)): return True
        return False

    def continue_rebasing(self):
        self.repo.git(c = "core.editor=true").rebase("--continue")

    def abort_rebasing(self):
        self.repo.git.rebase("--abort")

    def conflict_resolved(self, state: ConflictResolveState, paths: Optional[list[str]] = None):
        path_args = ["."] if paths is None else paths
        if state is ConflictResolveState.TAKE_OURS:
            self.repo.git.checkout("--ours", *path_args)
        elif state is ConflictResolveState.TAKE_THEIRS:
            self.repo.git.checkout("--theirs", *path_args)
        self.repo.git.add(*path_args)

    def launch_external_merge(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        if tool == "vscode" or tool == "code":
            if self._command_exists("code") == False:
                raise Exception("Could not find external Diff Tool")
            self.repo.git.config("merge.tool", "vscode")
            self.repo.git.config("mergetool.vscode.cmd", "code -n --wait $MERGED")
            self.repo.git.config("mergetool.writeToTemp", "true")
            tool = "vscode"
        if tool is None:
            raise Exception("No tool configured")
        if paths is not None:
            self.repo.git(c = "mergetool.keepBackup=false").mergetool(tool = tool, *paths)
        else:
            self.repo.git(c = "mergetool.keepBackup=false").mergetool(tool = tool)

    def launch_external_diff(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        if tool == "vscode" or tool == "code":
            if self._command_exists("code") == False:
                raise Exception("Could not find external Diff Tool")
            self.repo.git.config("diff.tool", "vscode")
            self.repo.git.config("difftool.vscode.cmd", "code -n --wait --diff $LOCAL $REMOTE")
            tool = "vscode"
        if tool is None:
            raise Exception("No tool configured")
        if paths is not None:
            self.repo.git.difftool("--no-prompt", tool = tool, *paths)
            self.repo.git.difftool("--no-prompt", "--cached", tool = tool, *paths)
        else:
            self.repo.git.difftool("--no-prompt", tool = tool)
            self.repo.git.difftool("--no-prompt", "--cached", tool = tool)

    def get_current_branch_name(self) -> str:
        return self.repo.git.branch("--show-current")

    def get_branches(self) -> list[Branch]:
        def _map_ref(ref) -> Branch:
            commit = ref.commit
            model = Branch(ref.name)
            model.id = commit.hexsha
            model.last_changed = commit.committed_datetime
            model.is_local = ref.is_remote == False
            return model

        branches = []
        local_branches = set()
        for ref in self.repo.branches:
            if ref.name == "HEAD": continue
            model = _map_ref(ref)
            branches.append(model)
            local_branches.add(model.name)
        for remote in self.repo.remotes:
            for ref in remote.refs:
                if "HEAD" in ref.name: continue
                model = _map_ref(ref)
                remote_prefix = f"{remote}/"
                if model.name.startswith(remote_prefix):
                    branch_name = model.name[len(remote_prefix):]
                    if branch_name in local_branches:
                        continue

                branches.append(model)

        return branches

    def get_current_change_id(self) -> str:
        return self.repo.git.rev_parse("HEAD")

    def get_remote_change_id(self) -> str:
        return self.repo.git.rev_parse("@{u}")

    def is_pull_required(self) -> bool:
        try:
            if self.is_unborn():
                changes = self.repo.iter_commits(rev="@{u}", max_count=1)
            else:
                changes = self.repo.iter_commits(rev="HEAD..@{u}", max_count=1)
            return next(changes, -1) != -1
        except:
            return False

    def is_push_required(self) -> bool:
        try:
            changes = self.repo.iter_commits(rev="@{u}..HEAD", max_count=1)
            return next(changes, -1) != -1
        except:
            return self.is_unborn() == False

    def has_remote(self) -> bool:
        return len(self.repo.remotes) > 0

    def _get_local_commits(self, has_upstream):
        if has_upstream:
            if self.is_unborn(): 
                return []
            return list(self.repo.iter_commits(rev="@{u}..HEAD"))
        else:
            if self.is_unborn():
                return []
            return list(self.repo.iter_commits())
        
    def get_local_commits(self):
        history = []
        local_commits = self._get_local_commits(self._has_upstream())
        
        for commit in local_commits:
            history.append(HistoryEntry(author=commit.author.email, id=commit.hexsha, message=commit.message, date=commit.committed_date, type=HistoryType.LOCAL))
        return history

    def get_new_commits(self, base, target):
        ids = set()
        commits = list(self.repo.iter_commits(rev=f"{target}..{base}"))
        for commit in commits:
            ids.add(commit.hexsha)

        remote = self._get_default_remote(base)
        if remote:
            base = remote + "/" + base
            commits = list(self.repo.iter_commits(rev=f"{target}..{base}"))    
            for commit in commits:
                ids.add(commit.hexsha)
        
        return ids

    def get_history(self, max_count: Optional[int] = None, skip: Optional[int] = None, rev_spec: Optional[str] = None):
        history = []
        args = {}
        if skip != None:
            args["skip"] = skip
        if max_count != None:
            args["max_count"] = max_count

        unborn = self.is_unborn()
        if not unborn:
            base_commits = list(self.repo.iter_commits(rev=rev_spec, **args))
        else:
            base_commits = []

        remote_commits = []
        local_commit_set = set()
        try:
            if self.has_remote():
                has_upstream = self._has_upstream()
                if has_upstream:
                    if unborn:
                        remote_commits = list(self.repo.iter_commits(rev="@{u}"))
                    else:
                        remote_commits = list(self.repo.iter_commits(rev="HEAD..@{u}"))
                
                if not unborn:
                    local_commits = self._get_local_commits(has_upstream)
                    for commit in local_commits:
                        local_commit_set.add(commit.hexsha)

        except Exception as e:
            pass
            
        for commit in base_commits:
            if self._is_head_detached():
                type = HistoryType.SYNCED
            else:
                type = HistoryType.LOCAL if commit.hexsha in local_commit_set else HistoryType.SYNCED
            history.append(HistoryEntry(author=commit.author.email, id=commit.hexsha, message=commit.message, date=commit.committed_date, type=type))

        for commit in remote_commits:
            history.append(HistoryEntry(author=commit.author.email, id=commit.hexsha, message=commit.message, date=commit.committed_date, type=HistoryType.REMOTE))

        return history

    def ignore(self, pattern: str, local_only = False):
        if local_only == False: 
            raise NotImplementedError()
        
        dir = os.path.join(self.repo.git_dir, "info")
        if not os.path.exists(dir):
            os.makedirs(dir)
        
        with open(os.path.join(dir, "exclude"), "a") as f:
            f.write(f"\n{pattern}")
            
    def prune_lfs(self):
        output = self.repo.git.lfs("prune")

        if "Deleting objects: 100%" not in output: return 0

        import re
        try:
            pruned_match = re.search("Deleting objects: 100% \(\d+\/\d+\), done", output)
            if pruned_match:
                return int(re.search("\d+\)", pruned_match.group()).group()[:-1])
        except:
            return 0        

    def _command_exists(self, cmd: str):
        return shutil.which(cmd) is not None

    def _is_head_detached(self):
        return self._get_current_branch() == "HEAD"

    def _get_current_branch(self):
        try:
            return self.repo.git.rev_parse("--abbrev-ref", "HEAD")
        except:
            return self.repo.active_branch

    def _get_default_remote(self, branch: str):
        try:
            return self.repo.git.config("--get", f"branch.{branch}.remote")
        except:
            return None

    def _get_file_changes(self, diff: git.Diff, changes: Changes):
        for change in diff.iter_change_type("M"):
            changes.modified_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("A"):
            changes.new_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("R"):
            changes.renamed_files.append(Change(path = change.b_path, old_path = change.a_path)) 
        for change in diff.iter_change_type("D"):
            changes.deleted_files.append(Change(path = change.a_path)) 

    def _make_relative_to_repo(self, path: str):
        if os.path.isabs(path):
            return os.path.relpath(path, self.repo.working_dir)
        else:
            return path

    def _get_repo_internal_dir(self):
        return os.path.join(self.repo.working_dir, ".git")