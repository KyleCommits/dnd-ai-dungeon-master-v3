import os
import json
from typing import Dict, Any
from enum import Enum, auto
from pathlib import Path

class RuleSection(Enum):
    CHARACTERIZATIONS = auto()
    CLASSES = auto()
    EQUIPMENT = auto()
    GAMEMASTERING = auto()
    GAMEPLAY = auto()
    MONSTERS = auto()
    RACES = auto()
    SPELLS = auto()
    TREASURE = auto()

class DnDRulesManager:
    def __init__(self):
        self.rules = {}
        self.rules_base_path = Path(__file__).parent.parent.parent / 'rules_md'
        self.rules_categories = {
            'Characterizations': [],
            'Classes': [],
            'Equipment': [],
            'Gamemastering': [],
            'Gameplay': [],
            'Monsters': [],
            'Races': [],
            'Spells': [],
            'Treasure': []
        }
        self.load_rules()
        
    def load_rules(self):
        """Load all rules from markdown files"""
        print("Loading D&D rules...")
        
        if not self.rules_base_path.exists():
            print(f"Rules directory not found at {self.rules_base_path}")
            return
            
        # Load each category
        for category in self.rules_categories.keys():
            category_path = self.rules_base_path / category
            if category_path.exists():
                md_files = list(category_path.glob('*.md'))
                self.rules_categories[category] = [
                    self._load_markdown_file(file_path) 
                    for file_path in md_files
                ]
                print(f"  • {category}: {len(md_files)} files")
                
    def _load_markdown_file(self, file_path: Path) -> dict:
        """Load a single markdown file and return its content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return {
                    'name': file_path.stem,
                    'category': file_path.parent.name,
                    'content': content
                }
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def get_relevant_rules(self, action: str, max_tokens: int = 4000) -> str:
        """Get rules relevant to a specific action"""
        action_words = set(action.lower().split())
        relevant_sections = []
        
        # Search through all categories and files
        for category, rules in self.rules_categories.items():
            for rule in rules:
                if not rule:  # Skip any None entries
                    continue
                    
                # Check if any action words appear in the rule content
                content = rule['content'].lower()
                if any(word in content for word in action_words):
                    summary = (
                        f"[{category}/{rule['name']}]\n"
                        f"{rule['content'][:500]}..."  # First 500 chars as preview
                    )
                    relevant_sections.append(summary)
        
        if not relevant_sections:
            return "No specific rules found for this action."
            
        # Combine relevant sections, respecting token limit
        combined = "\n\n".join(relevant_sections)
        if len(combined) > max_tokens:
            combined = combined[:max_tokens] + "\n[Content truncated due to length...]"
            
        return combined

    def get_rules_section(self, section_name: str) -> str:
        """Get rules for a specific section"""
        # First check if it's a category
        if section_name in self.rules_categories:
            sections = [
                rule['content'] 
                for rule in self.rules_categories[section_name] 
                if rule is not None
            ]
            return "\n\n".join(sections)
            
        # Then look through all categories for matching file
        for category, rules in self.rules_categories.items():
            for rule in rules:
                if rule and rule['name'].lower() == section_name.lower():
                    return rule['content']
                    
        print(f"⚠️ Rule section '{section_name}' not found.")
        print(f"Available sections: {', '.join(sorted(self.rules_categories.keys()))}")
        return ""