#!/usr/bin/env python3
"""
Script to fix all get_database() calls to be properly awaited
"""

import os
import re

def fix_file(file_path):
    """Fix get_database() calls in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all get_database() calls that are not awaited
        pattern = r'(\s+)db = get_database\(\)'
        replacement = r'\1db = await get_database()'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Fixed {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all router files"""
    router_dir = "app/routers"
    files_to_fix = [
        "attendance.py",
        "cafeteria.py", 
        "maps.py",
        "schedule.py",
        "users.py"
    ]
    
    fixed_count = 0
    total_files = len(files_to_fix)
    
    for filename in files_to_fix:
        file_path = os.path.join(router_dir, filename)
        if os.path.exists(file_path):
            if fix_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n🎯 Summary: Fixed {fixed_count}/{total_files} files")
    
    if fixed_count == total_files:
        print("✅ All database calls have been fixed!")
    else:
        print("⚠️  Some files may still need manual fixing")

if __name__ == "__main__":
    main()
