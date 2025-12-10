"""Find all Wikipedia pages scraped about Công Phượng"""
import os
import glob

# Check raw data directory
raw_dir = "data/raw"
parsed_dir = "data/parsed"

print("=" * 60)
print("SEARCHING FOR CÔNG PHƯỢNG DATA FILES")
print("=" * 60)

# Search in raw directory
print(f"\n📂 Searching in {raw_dir}/")
if os.path.exists(raw_dir):
    files = glob.glob(f"{raw_dir}/**/*cong*phuong*", recursive=True) + \
            glob.glob(f"{raw_dir}/**/*Công*Phượng*", recursive=True) + \
            glob.glob(f"{raw_dir}/**/*Nguyen_Cong_Phuong*", recursive=True)
    
    if files:
        print(f"✅ Found {len(files)} files:")
        for f in files[:20]:
            print(f"   - {f}")
            # Try to read first few lines
            if f.endswith('.txt') or f.endswith('.json'):
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        content = file.read(500)
                        print(f"      Preview: {content[:200]}...")
                except:
                    pass
    else:
        print("❌ No files found")
else:
    print(f"❌ Directory {raw_dir} does not exist")

# Search in parsed directory
print(f"\n📂 Searching in {parsed_dir}/")
if os.path.exists(parsed_dir):
    files = glob.glob(f"{parsed_dir}/**/*cong*phuong*", recursive=True) + \
            glob.glob(f"{parsed_dir}/**/*Công*Phượng*", recursive=True) + \
            glob.glob(f"{parsed_dir}/**/*Nguyen_Cong_Phuong*", recursive=True)
    
    if files:
        print(f"✅ Found {len(files)} files:")
        for f in files[:20]:
            print(f"   - {f}")
    else:
        print("❌ No files found")
else:
    print(f"❌ Directory {parsed_dir} does not exist")

# List all raw files to see naming pattern
print(f"\n📋 All files in {raw_dir}/ (first 30):")
if os.path.exists(raw_dir):
    all_files = []
    for root, dirs, files in os.walk(raw_dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    for f in sorted(all_files)[:30]:
        print(f"   - {f}")
    print(f"\n   Total: {len(all_files)} files")
