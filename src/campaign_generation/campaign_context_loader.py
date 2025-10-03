# src/campaign_generation/campaign_context_loader.py
import os
import logging
from typing import List, Dict, Any
from pathlib import Path

class CampaignContextLoader:
    """Loads and manages WotC campaign examples for context injection"""

    def __init__(self, campaigns_dir: str = "dnd_src_material/campaigns"):
        self.campaigns_dir = Path(campaigns_dir)
        self.logger = logging.getLogger(__name__)

    def load_campaign_file(self, filename: str) -> str:
        """Load a single campaign file and return its content"""
        file_path = self.campaigns_dir / filename

        if not file_path.exists():
            print(f"WARNING: Campaign file not found: {file_path}")
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.logger.info(f"Loaded campaign: {filename} ({len(content)} chars)")
            return content

        except Exception as e:
            self.logger.error(f"Failed to load campaign {filename}: {e}")
            return ""

    def get_example_campaigns(self, count: int = 3) -> List[Dict[str, str]]:
        """Get the best example campaigns for context injection"""

        # Priority list of best WotC campaigns for examples
        priority_campaigns = [
            "Baldur's Gate_ Descent Into Avernus.md",
            "Curse of Strahd.md",
            "Waterdeep_ Dragon Heist.md",
            "Tomb of Annihilation.md",
            "Storm King's Thunder.md"
        ]

        examples = []

        for campaign_file in priority_campaigns[:count]:
            content = self.load_campaign_file(campaign_file)
            if content:
                examples.append({
                    "filename": campaign_file,
                    "title": campaign_file.replace('.md', '').replace('_', ' '),
                    "content": content,
                    "length": len(content)
                })

        self.logger.info(f"Loaded {len(examples)} example campaigns for context")
        return examples

    def create_massive_context(self, user_prompt: str, stage: str) -> str:
        """Create massive context string for Gemini with full campaign examples"""

        examples = self.get_example_campaigns(3)

        context_parts = [
            f"# CAMPAIGN GENERATION CONTEXT - {stage.upper()}",
            f"",
            f"## USER REQUEST",
            f"{user_prompt}",
            f"",
            f"## PROFESSIONAL CAMPAIGN EXAMPLES",
            f"Study these complete, professional D&D campaigns. Your generated campaign must match this depth, detail, and structure:",
            f""
        ]

        for i, example in enumerate(examples, 1):
            context_parts.extend([
                f"### EXAMPLE {i}: {example['title']} ({example['length']} characters)",
                f"```markdown",
                example['content'],
                f"```",
                f""
            ])

        context_parts.extend([
            f"## GENERATION REQUIREMENTS",
            f"- Match the LENGTH and DEPTH of the examples above (5,000-7,000 lines)",
            f"- Use the same STRUCTURE and FORMATTING as professional campaigns",
            f"- Include rich NPC descriptions, detailed locations, complex plots",
            f"- Maintain professional D&D writing quality throughout",
            f"",
            f"## YOUR TASK FOR {stage.upper()}:",
            f"Generate content that matches the professional quality shown above."
        ])

        full_context = "\n".join(context_parts)

        self.logger.info(f"Created massive context: {len(full_context)} characters for {stage}")
        return full_context

    def get_condensed_examples(self, count: int = 5) -> str:
        """Get condensed campaign summaries for XAI (fits in 32k tokens)"""

        examples = self.get_example_campaigns(count)
        summaries = []

        for example in examples:
            # Extract key sections for summary
            lines = example['content'].split('\n')
            summary_lines = []

            # Get title, description, plot structure
            in_important_section = False
            section_line_count = 0

            for line in lines:
                line = line.strip()

                # Include headers and first few lines of each section
                if line.startswith('#') or line.startswith('##'):
                    in_important_section = True
                    section_line_count = 0
                    summary_lines.append(line)
                elif in_important_section and section_line_count < 3 and line:
                    summary_lines.append(line)
                    section_line_count += 1
                elif section_line_count >= 3:
                    in_important_section = False

            condensed = '\n'.join(summary_lines[:100])  # Limit per campaign
            summaries.append(f"## {example['title']}\n{condensed}")

        condensed_context = "\n\n".join(summaries)
        self.logger.info(f"Created condensed context: {len(condensed_context)} characters")

        return condensed_context