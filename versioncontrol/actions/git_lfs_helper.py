import os
import mimetypes

try:
    from binaryornot.check import is_binary
except:
    import anchorpoint
    ctx = anchorpoint.Context.instance()
    ctx.install("binaryornot")
    from binaryornot.check import is_binary

def _file_bytes_binary(path: str):
    return is_binary(path)

def _file_is_binary(path: str):
    mime_type = mimetypes.guess_type(path)
    if not mime_type: return _file_bytes_binary(path)
    if not isinstance(mime_type[0],str): return _file_bytes_binary(path)
    
    type = mime_type[0]
    if type == "text": return False
    if type != "application": return True
    if not isinstance(mime_type[1],str): return _file_bytes_binary(path)
    
    subtype = mime_type[1] 
    if subtype not in ["json", "ld+json", "x-httpd-php", "x-sh", "x-csh", "xhtml+xml", "xml", "svg", "svg+xml"]:
        return _file_bytes_binary(path)
    return False

def _collect_binary_extensions(paths) -> set[str]:
    collected_extensions = set()
    for path in paths:
        split = os.path.splitext(path)
        if len(split) < 2: continue
        extension = split[1]
        if _file_is_binary(path):                
            collected_extensions.add(extension)

    return collected_extensions

def lfs_track_binary_files(paths, repo):
    extensions = _collect_binary_extensions(paths)
    repo.track_lfs(extensions)
    paths.append(".gitattributes")