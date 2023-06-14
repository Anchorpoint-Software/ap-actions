import os, pathlib
import mimetypes

from binaryornot.check import is_binary

def _is_file_filtered(path: str):
    file = pathlib.Path(path).stem
    return file in [".DS_Store"]

def _file_bytes_binary(path: str):
    if not os.path.exists(path): return False
    return is_binary(path) and not _is_file_filtered(path)

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

def _collect_binaries(paths, repo, progress_callback = None):
    max_count = len(paths) - 1
    collected_extensions = set()
    collected_paths = set()
    for count, path in enumerate(paths):
        if progress_callback: 
            cont = progress_callback(count+1, max_count)
            if not cont:
                return None, None, True
        if os.path.isdir(path): continue
        split = os.path.splitext(path)
        if len(split) < 2: continue
        extension = split[1]
        if extension in collected_extensions or path in collected_paths: 
            continue

        if _file_is_binary(path):        
            if len(extension) == 0:     
                collected_paths.add(path)
            else:
                collected_extensions.add(extension)

    return collected_paths, collected_extensions, False

def lfs_track_binary_files(paths, repo, progress_callback = None):
    binary_paths, binary_extensions, canceled = _collect_binaries(paths, repo, progress_callback)
    if canceled:
        return
    add_gitattributes = False
    
    if len(binary_extensions) > 0:
        repo.track_lfs(binary_extensions)
        add_gitattributes = True
    if len(binary_paths) > 0:
        repo.track_lfs_files(binary_paths)
        add_gitattributes = True
        
    if add_gitattributes:
        paths.append(".gitattributes")

class LFSExtensionTracker:
    def __init__(self, repo) -> None:
        self.gitattributes_path = os.path.join(repo.get_root_path(), '.gitattributes')
        self.lfs_patterns = []
        if not os.path.exists(self.gitattributes_path):
            return
        
        with open(self.gitattributes_path, 'r') as f:
            for line in f.readlines():
                if line.startswith('#'): continue
                if 'filter=lfs' in line:
                    self.lfs_patterns.append(line.split()[0])
    
    def is_extension_tracked(self, extension):
        for pattern in self.lfs_patterns:
            if pattern == f'*.{extension}':
                return True
        return False
    
    def is_file_tracked(self, path):
        try:
            extension = os.path.splitext(path)[1]
            return self.is_extension_tracked(extension[1:])
        except:
            return False