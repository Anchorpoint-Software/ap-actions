import anchorpoint

try:
    import vc.apgit.utility as utility
    import os
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = utility.get_git_cmd_path().replace("\\","/")

    if utility.guarantee_git():
        try: 
            import git
        except:
            raise Warning("Git not installed")
    else: raise Warning("Git not installed")

except Exception as e:
    raise e