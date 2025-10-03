import os

directory = r"C:\Users\kylej\Documents\Github\dungeon_master_discord_bot\dungeon-master-bot\rules_md"

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.md'):
            full_path = os.path.join(root, file)
            print(full_path)