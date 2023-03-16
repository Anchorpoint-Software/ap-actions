import platform, os, requests, zipfile, io, shutil, stat
import anchorpoint as ap

if platform.system() == "Darwin":
    FFMPEG_INSTALL_URL = "https://s3.eu-central-1.amazonaws.com/releases.anchorpoint.app/ffmpeg/ffmpeg.zip"
    FFMPEG_ZIP_PATH = "ffmpeg/ffmpeg"
else:
    FFMPEG_INSTALL_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    FFMPEG_ZIP_PATH = "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe"

ffmpeg_folder_path = "~/Documents/Anchorpoint/actions/ffmpeg"

def _get_ffmpeg_dir():
    dir = os.path.expanduser(ffmpeg_folder_path)
    return os.path.normpath(dir)

def get_ffmpeg_fullpath():
    dir = os.path.expanduser(ffmpeg_folder_path)
    if platform.system() == "Darwin":
        dir = os.path.join(dir, "ffmpeg")
    else: 
        dir = os.path.join(dir, "ffmpeg.exe")
    return os.path.normpath(dir)

def _install_ffmpeg_async(callback, *args, **kwargs):
    ctx = ap.get_context()
    if not os.path.isdir(_get_ffmpeg_dir()):
        os.mkdir(_get_ffmpeg_dir())
    
    # download zip
    progress = ap.Progress("Installing FFmpeg", infinite = True)
    r = requests.get(FFMPEG_INSTALL_URL)
            
    # open zip file and extract ffmpeg.exe to the right folder
    z = zipfile.ZipFile(io.BytesIO(r.content))
    
    with z.open(FFMPEG_ZIP_PATH) as source:
        with open(get_ffmpeg_fullpath(), "wb") as target:
            shutil.copyfileobj(source, target)

    if platform.system() == "Darwin":
        os.chmod(get_ffmpeg_fullpath(), stat.S_IRWXU)

    progress.finish()
    ctx.run_async(callback, *args, **kwargs)

def _install_ffmpeg(dialog, callback, *args, **kwargs):
    ap.get_context().run_async(_install_ffmpeg_async, callback, *args, **kwargs)
    dialog.close()

def _ffmpeg_install_dialog(callback, *args, **kwargs):
    dialog = ap.Dialog()
    dialog.title = "Install Conversion Tools"
    dialog.add_text("Anchorpoint's video conversion tools are based on FFmpeg.")
    dialog.add_info("When installing <a href=\"http://ffmpeg.org\">FFmpeg</a> you are accepting the <a href=\"http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html\">license</a> of the owner.")
    dialog.add_button("Install", callback=lambda d: _install_ffmpeg(d, callback, *args, **kwargs))
    dialog.show()

def guarantee_ffmpeg(callback, *args, **kwargs):
    ctx = ap.get_context()

    # First, check if the tool can be found on the machine
    ffmpeg_path = get_ffmpeg_fullpath()
    
    # check for ffmpeg.exe and download if missing
    if not os.path.isfile(ffmpeg_path):
        _ffmpeg_install_dialog(callback, *args, **kwargs)
    else:
        ctx.run_async(callback, *args, **kwargs)