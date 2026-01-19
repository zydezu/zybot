import os, shutil, sys
from pathlib import Path
import git

def download_repo(url):
    print("Cloning from git...")

    clone_directory = 'tempgitclonedir/'
    if delete_folder(clone_directory):
        repo = git.Repo.clone_from(url, clone_directory, depth=5)
    else:
        repo = git.Repo.init(clone_directory)
        origin = repo.create_remote('origin', url)
        origin.fetch()
        repo.git.reset('--hard', 'origin/main')

    print("Last 5 commits and changes:")
    for commit in list(repo.iter_commits(max_count=5)):
        print(f"{commit.message.strip()} ({commit.author.name})")

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
                print(f"Error moving file {each_item}: {e}")

    print("Cleaning up...")
    try:
        delete_folder(src_path)
    except Exception as e:
        print(f"Cleanup failed: {e}")
    print("Git download complete!")

def delete_folder(folder_path):
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Successfully deleted {folder_path}")
            return True
        except Exception as e:
            print(f"Failed to delete {folder_path}: {e}")
            return False
    else:
        print(f"Folder does not exist: {folder_path}")
        return False

def start_git_clone():
    try:
        with open("gitFilePath.txt", "r") as f:
            filepath = f.readline().strip()
            print(f"Starting git clone from: {filepath}")
            download_repo(filepath)
    except Exception as e:
        print(f"Failed to read gitFilePath.txt: {e}")

def restart_bot():
    print("Git cloning...")
    start_git_clone()
    print("Restarting bot...")
    sys.exit(1)