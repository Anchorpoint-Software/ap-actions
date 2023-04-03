import anchorpoint

try:
    import vc.apgit.utility as utility
    import vc.apgit_utility.install_git as install_git
    import os
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = install_git.get_git_cmd_path().replace("\\","/")
    
    import logging
    if logging.getLogger().level == logging.DEBUG:
        os.environ["GIT_PYTHON_TRACE"] = "full"
        
    if utility.guarantee_git():
        try: 
            import git
        except:
            raise Warning("GitPython is not installed")
    else: raise Warning("Git not installed")

except Exception as e:
    raise e