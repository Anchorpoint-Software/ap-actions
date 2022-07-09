import os
import mimetypes

from binaryornot.check import is_binary

def _file_bytes_binary(path: str):
    return is_binary(path)

def _file_is_binary(path: str):
    mime_type = mimetypes.guess_type(path)
    if not mime_type: return _file_bytes_binary(path)
    if not isinstance(mime_type[0],str): return _file_bytes_binary(path)
    
    type_split = mime_type[0].split("/")
    if len(type_split) != 2: return _file_bytes_binary(path)
    
    type = type_split[0]
    subtype = type_split[1]

    if type == "text": return False
    if subtype not in ["json", "ld+json", "x-httpd-php", "x-sh", "x-csh", "xhtml+xml", "xml", "svg", "svg+xml"]:
        return _file_bytes_binary(path)

    return False

def _collect_binaries(paths, repo) -> set[str]:
    collected_extensions = set()
    collected_paths = set()
    for path in paths:
        split = os.path.splitext(path)
        if len(split) < 2: continue
        extension = split[1]
        if _file_is_binary(path):        
            if len(extension) == 0:     
                collected_paths.add(path)
            else:
                collected_extensions.add(extension)

    return collected_paths, collected_extensions

def lfs_track_binary_files(paths, repo):
    binary_paths, binary_extensions = _collect_binaries(paths, repo)
    add_gitattributes = False
    
    if len(binary_extensions) > 0:
        repo.track_lfs(binary_extensions)
        add_gitattributes = True
    if len(binary_paths) > 0:
        repo.track_lfs_files(binary_paths)
        add_gitattributes = True
        
    if add_gitattributes:
        paths.append(".gitattributes")
