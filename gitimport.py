import os, shutil, sys, logging
from pathlib import Path
import git

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("umkl_server.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def normalized_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """
    Recursively converts a size in bytes to a human-readable string with appropriate units.

    Args:
        bytes (float): The size in bytes to be converted.
        units (list of str, optional): A list of units to use for conversion. Defaults to 
                                       [' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'].

    Returns:
        str: The size converted to a human-readable string with the appropriate unit.
    """
    if bytes < 1024 or len(units) == 1:
        return f"{round(bytes, 2):.2f}{units[0]}"
    else:
        return normalized_size(bytes / 1024, units[1:])

def download_repo(url):
    log.info("Cloning from git...")

    clone_directory = 'tempgitclonedir/'
    if delete_folder(clone_directory):
        repo = git.Repo.clone_from(url, clone_directory, depth=5)
    else:
        repo = git.Repo.init(clone_directory)
        origin = repo.create_remote('origin', url)
        origin.fetch()
        repo.git.reset('--hard', 'origin/main')

    log.info("Last 5 commits and changes:")
    for commit in list(repo.iter_commits(max_count=5)):
        log.info(f"{commit.message.strip()} ({commit.author.name})")

    repo.close()

    # Recursively move all files and subfolders
    src_path = Path(clone_directory)
    trg_path = src_path.parent
    for each_item in src_path.rglob('*'):
        relative_path = each_item.relative_to(src_path)
        trg_item_path = trg_path.joinpath(relative_path)

        if each_item.is_dir():
            trg_item_path.mkdir(parents=True, exist_ok=True)
        else:
            try:
                shutil.move(str(each_item), str(trg_item_path))
            except Exception as e:
                log.error(f"Error moving file {each_item}: {e}")

    log.info("Cleaning up...")
    try:
        delete_folder(src_path)
    except Exception as e:
        log.warning(f"Cleanup failed: {e}")
    log.info("Git download complete!")

def delete_folder(folder_path):
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            log.info(f"Successfully deleted {folder_path}")
            return True
        except Exception as e:
            log.warning(f"Failed to delete {folder_path}: {e}")
            return False
    else:
        log.warning(f"Folder does not exist: {folder_path}")
        return False

def start_git_clone():
    try:
        with open("gitFilePath.txt", "r") as f:
            filepath = f.readline().strip()
            log.info(f"Starting git clone from: {filepath}")
            download_repo(filepath)
    except Exception as e:
        log.error(f"Failed to read gitFilePath.txt: {e}")

def restart_bot():
    log.info("Git cloning...")
    start_git_clone()
    log.info("Restarting bot...")
    sys.exit(1)