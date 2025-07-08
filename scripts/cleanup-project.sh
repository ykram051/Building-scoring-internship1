#!/bin/bash
# Project Cleanup Script
# This script removes unnecessary files and organizes the project structure

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting project cleanup..."

# List of files to be removed (empty or redundant)
FILES_TO_REMOVE=(
    # Empty/redundant batch files
    "run.bat"
    "run_fixed.bat"
    "run_with_db.bat"
    "run_with_init.bat"
    "backup_database.bat"
    "restore_database.bat"
    "setup_docker_db.bat"
    "docker-start.bat"
    
    # Empty/redundant PowerShell scripts
    "Run.ps1"
    "Run-Dashboard.ps1"
    "Run-Direct-Access.ps1"
    "Run-Direct.ps1"
    
    # Redundant shell scripts (we'll consolidate these)
    "Cleanup-Project.ps1" # Moving to scripts folder
    
    # Redundant documentation
    "SIMPLIFIED_README.md"
    
    # Redundant markdown files
    "QUICKSTART.md" # We'll merge content into README.md
)

# Remove the files
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        rm -f "$SCRIPT_DIR/$file"
        echo "Removed: $file"
    else
        echo "File not found: $file - already removed"
    fi
done

# Clean up pycache directories
find "$SCRIPT_DIR" -type d -name "__pycache__" | while read dir; do
    rm -rf "$dir"
    echo "Removed pycache directory: $dir"
done

# Clean up cache files that are not needed
if [ -d "$SCRIPT_DIR/app/cache" ]; then
    rm -f "$SCRIPT_DIR/app/cache"/*
    echo "Removed cache files"
fi

# Create a scripts directory for all scripts if it doesn't exist
if [ ! -d "$SCRIPT_DIR/scripts" ]; then
    mkdir -p "$SCRIPT_DIR/scripts"
    echo "Created scripts directory"
fi

# Move all shell and PowerShell scripts to scripts directory, except the main launchers
echo "Moving scripts to scripts directory..."
for script in $(find "$SCRIPT_DIR" -maxdepth 1 -type f \( -name "*.sh" -o -name "*.ps1" \) | grep -v -E 'run.sh|run_with_db.sh|run_with_init.sh|Run-App.ps1|Run-Strict-DB.ps1|Run-With-Init.ps1|cleanup-project.sh'); do
    filename=$(basename "$script")
    cp "$script" "$SCRIPT_DIR/scripts/$filename"
    rm -f "$script"
    echo "Moved $filename to scripts directory"
done

# Create a docs directory and move all markdown and documentation files there
if [ ! -d "$SCRIPT_DIR/docs" ]; then
    mkdir -p "$SCRIPT_DIR/docs"
    echo "Created docs directory"
fi

# Move documentation files to docs directory, except the main README.md
echo "Moving documentation to docs directory..."
for doc in $(find "$SCRIPT_DIR" -maxdepth 1 -type f \( -name "*.md" -o -name "*.html" \) | grep -v 'README.md'); do
    filename=$(basename "$doc")
    cp "$doc" "$SCRIPT_DIR/docs/$filename"
    rm -f "$doc"
    echo "Moved $filename to docs directory"
done

echo ""
echo "Project cleanup completed!"
echo "Updated project structure is now cleaner and more organized."

# Make all shell scripts executable
find "$SCRIPT_DIR" -name "*.sh" -exec chmod +x {} \;
echo "Made all shell scripts executable"
