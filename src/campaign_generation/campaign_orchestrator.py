# src/campaign_generation/campaign_orchestrator.py
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json

from .stage_managers import (
    LocalCampaignOutlineStage,
    LocalPlotStructureStage,
    DetailedContentStage,
    NPCLocationStage
)
from ..campaign_manager import create_and_index_campaign

class CampaignOrchestrator:
    """Orchestrates the complete 6-stage campaign generation process"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stages = [
            ("Campaign Outline", LocalCampaignOutlineStage()),
            ("Plot Structure", LocalPlotStructureStage()),
            ("Detailed Content", DetailedContentStage()),
            ("NPC & Location Polish", NPCLocationStage())
        ]

    async def generate_campaign(self, user_prompt: str,
                              progress_callback: Optional[Callable[[str, int, int], None]] = None,
                              stage_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Generate a complete professional-quality campaign

        Args:
            user_prompt: User's campaign request
            progress_callback: Called with (message, current_stage, total_stages)
            stage_callback: Called with (stage_name, stage_results)

        Returns:
            Complete campaign data with all stages
        """

        start_time = time.time()
        self.logger.info(f"Starting campaign generation: {user_prompt}")

        results = {"user_prompt": user_prompt, "generation_start": start_time}
        total_stages = len(self.stages)

        try:
            for stage_index, (stage_name, stage_manager) in enumerate(self.stages, 1):
                stage_start = time.time()

                if progress_callback:
                    await progress_callback(f"Starting {stage_name}...", stage_index, total_stages)

                self.logger.info(f"Executing Stage {stage_index}/{total_stages}: {stage_name}")

                # Create progress callback for this stage
                async def stage_progress(message: str):
                    if progress_callback:
                        await progress_callback(f"{stage_name}: {message}", stage_index, total_stages)

                # Execute the stage
                stage_result = await stage_manager.execute(user_prompt, results, stage_progress)

                # Merge results
                results.update(stage_result)

                stage_duration = time.time() - stage_start
                self.logger.info(f"Completed {stage_name} in {stage_duration:.1f}s")

                if stage_callback:
                    await stage_callback(stage_name, stage_result)

                # Brief pause between stages
                await asyncio.sleep(1)

            # Final assembly
            final_campaign = await self._assemble_final_campaign(results)

            total_duration = time.time() - start_time
            self.logger.info(f"Campaign generation completed in {total_duration:.1f}s")

            if progress_callback:
                await progress_callback("Campaign generation complete!", total_stages, total_stages)

            return final_campaign

        except Exception as e:
            self.logger.error(f"Campaign generation failed: {e}")
            if progress_callback:
                await progress_callback(f"Generation failed: {str(e)}", stage_index, total_stages)
            raise

    async def _assemble_final_campaign(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble all stage results into final campaign document"""

        outline = results.get("outline", {})
        plot_structure = results.get("plot_structure", {})
        detailed_content = results.get("detailed_content", "")
        polished_content = results.get("polished_content", "")

        # Combine content intelligently
        final_content = detailed_content
        if polished_content and len(polished_content) > 1000:
            final_content = polished_content

        # Create metadata
        metadata = {
            "generation_method": "hybrid_6_stage",
            "generation_time": time.time() - results.get("generation_start", 0),
            "stages_completed": list(results.keys()),
            "estimated_quality": "professional",
            "content_length": len(final_content),
            "word_count": len(final_content.split()) if final_content else 0,
            "line_count": len(final_content.split('\n')) if final_content else 0
        }

        final_campaign = {
            "title": outline.get("title", "Generated Campaign"),
            "description": outline.get("core_concept", "An epic D&D adventure"),
            "themes": outline.get("themes", []),
            "estimated_sessions": outline.get("estimated_sessions", 30),
            "central_mystery": outline.get("central_mystery", ""),
            "acts": outline.get("acts", {}),
            "key_npcs": outline.get("key_npcs", []),
            "key_locations": outline.get("key_locations", []),
            "plot_structure": plot_structure,
            "content": final_content,
            "metadata": metadata,
            "generation_results": results  # Keep all stage data for debugging
        }

        self.logger.info(f"Assembled final campaign: {metadata['line_count']} lines, {metadata['word_count']} words")
        return final_campaign

    async def save_campaign(self, campaign_data: Dict[str, Any]) -> str:
        """Save generated campaign to markdown file and create RAG index"""

        try:
            # Use the existing campaign manager that handles both file saving and RAG indexing
            sanitized_title = await create_and_index_campaign(campaign_data)

            # Return the full path for compatibility
            output_path = f"dnd_src_material/custom_campaigns/{sanitized_title}.md"
            self.logger.info(f"Saved and indexed campaign: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to save and index campaign: {e}")
            raise

    def _create_markdown_content(self, campaign_data: Dict[str, Any]) -> str:
        """Convert campaign data to properly formatted markdown"""

        title = campaign_data.get("title", "Generated Campaign")
        description = campaign_data.get("description", "")
        themes = campaign_data.get("themes", [])
        sessions = campaign_data.get("estimated_sessions", 30)
        mystery = campaign_data.get("central_mystery", "")
        acts = campaign_data.get("acts", {})
        npcs = campaign_data.get("key_npcs", [])
        locations = campaign_data.get("key_locations", [])
        content = campaign_data.get("content", "")
        metadata = campaign_data.get("metadata", {})

        markdown_parts = [
            f"# {title}",
            "",
            "## Campaign Overview",
            f"**Description:** {description}",
            f"**Estimated Sessions:** {sessions}",
            f"**Themes:** {', '.join(themes) if themes else 'Adventure, Heroism'}",
            f"**Central Mystery:** {mystery}",
            ""
        ]

        # Add act structure
        if acts:
            markdown_parts.extend([
                "## Campaign Structure",
                ""
            ])

            for act_key, act_data in acts.items():
                if isinstance(act_data, dict):
                    markdown_parts.extend([
                        f"### {act_data.get('title', act_key.title())}",
                        f"**Sessions:** {act_data.get('sessions', 'Unknown')}",
                        f"**Summary:** {act_data.get('summary', 'To be determined')}",
                        ""
                    ])

        # Add NPCs
        if npcs:
            markdown_parts.extend([
                "## Key NPCs",
                ""
            ])

            for npc in npcs:
                if isinstance(npc, dict):
                    markdown_parts.extend([
                        f"### {npc.get('name', 'Unknown NPC')}",
                        f"**Role:** {npc.get('role', 'Unknown')}",
                        f"**Importance:** {npc.get('importance', 'Supporting character')}",
                        ""
                    ])

        # Add locations
        if locations:
            markdown_parts.extend([
                "## Key Locations",
                ""
            ])

            for location in locations:
                if isinstance(location, dict):
                    markdown_parts.extend([
                        f"### {location.get('name', 'Unknown Location')}",
                        f"**Type:** {location.get('type', 'Unknown')}",
                        f"**Importance:** {location.get('importance', 'Minor location')}",
                        ""
                    ])

        # Add detailed content
        if content and len(content) > 100:
            markdown_parts.extend([
                "## Detailed Campaign Content",
                "",
                content,
                ""
            ])

        # Add generation metadata
        markdown_parts.extend([
            "---",
            "## Generation Metadata",
            f"- **Generation Method:** {metadata.get('generation_method', 'Unknown')}",
            f"- **Content Length:** {metadata.get('line_count', 0)} lines, {metadata.get('word_count', 0)} words",
            f"- **Generation Time:** {metadata.get('generation_time', 0):.1f} seconds",
            f"- **Quality Estimate:** {metadata.get('estimated_quality', 'Unknown')}",
            ""
        ])

        return "\n".join(markdown_parts)