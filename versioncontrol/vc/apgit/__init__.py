try:
    import vc.apgit.utility as utility
    import vc.apgit_utility.install_git as install_git
    import os

    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = install_git.get_git_cmd_path().replace(
        "\\", "/"
    )

    import logging

    if logging.getLogger().level == logging.DEBUG:
        os.environ["GIT_PYTHON_TRACE"] = "full"

    if utility.setup_git():
        try:
            pass
        except Exception as e:
            print(f"Error importing GitPython: {e}")
            raise Warning("GitPython is not installed")
    else:
        raise Warning("Git not installed")

except Exception as e:
    raise e
