import anchorpoint

try:
    import vc.apgit.utility as utility
    import vc.apgit_utility.install_git as install_git
    import os
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = install_git.get_git_cmd_path().replace("\\","/")
    
    # User can enable tracing by setting environment variable (set GIT_PYTHON_TRACE=full)
    # os.environ["GIT_PYTHON_TRACE"] = "full"
    if "GIT_PYTHON_TRACE" in os.environ:
        import logging
        logging.basicConfig()
        logging.root.setLevel(logging.INFO)
        
    if utility.guarantee_git():
        try: 
            import git
        except:
            raise Warning("GitPython is not installed")
    else: raise Warning("Git not installed")

except Exception as e:
    raise e