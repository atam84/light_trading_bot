# fix_init_files.py

"""
#Fix Missing __init__.py Files
#Ensures all directories have proper __init__.py files for Python imports
"""

import os
from pathlib import Path

def create_init_files():
    """Create missing __init__.py files"""
    
    directories_needing_init = [
        "src",
        "src/core",
        "src/database", 
        "src/database/models",
        "src/database/repositories",
        "src/clients",
        "src/interfaces",
        "src/interfaces/web",
        "src/interfaces/cli",
        "src/interfaces/telegram",
        "src/strategies",
        "src/utils"
    ]
    
    print("🔧 Fixing missing __init__.py files...")
    
    for directory in directories_needing_init:
        dir_path = Path(directory)
        init_file = dir_path / "__init__.py"
        
        # Create directory if it doesn't exist
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py if it doesn't exist or is empty
        if not init_file.exists() or init_file.stat().st_size == 0:
            with open(init_file, 'w') as f:
                f.write(f'"""{"{}".format(directory.replace("/", ".")).replace("src.", "")} module"""\n')
            print(f"   ✅ Created {init_file}")
        else:
            print(f"   ✓ {init_file} already exists")
    
    print("✅ All __init__.py files are in place!")

if __name__ == "__main__":
    create_init_files()


