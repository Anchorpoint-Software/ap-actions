import anchorpoint as ap
import os
import platform, sys

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        sys.path.insert(0, os.path.split(__file__)[0])
        import is_git_repo as git
        return git.is_git_repo(path)
    except Exception as e:
        print(str(e))
    return False


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_git_cmd_path

    env = GitRepository.get_git_environment()
    for key,value in env.items():
        os.putenv(key, value)

    ctx = ap.Context.instance()
    if platform.system() == "Darwin":
        os.system(f"open -a Terminal \"{ctx.path}\"")
    elif platform.system() == "Windows":
        path = os.environ["PATH"]
        os.putenv("PATH", f"{os.path.dirname(get_git_cmd_path())};{path}")
        os.system(f"start cmd /k cd \"{ctx.path}\"")