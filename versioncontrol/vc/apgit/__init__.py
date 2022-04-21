try:
    import anchorpoint
    ctx = anchorpoint.Context.instance()
    try: 
        import git
    except:
        ctx.install("GitPython")
        import git

except:
    print("Not running Anchorpoint")