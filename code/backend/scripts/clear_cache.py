import os
import shutil

def clear_cache():
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(cache_path)
            print(f"Deleted {cache_path}")

if __name__ == "__main__":
    clear_cache()