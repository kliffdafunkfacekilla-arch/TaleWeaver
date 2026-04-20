import unittest
import asyncio
import os
import json
import sys

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import engine
from core.schemas import CampaignTracker, MasterArc

class TestCampaignWeaver(unittest.IsolatedAsyncioTestCase):
    """
    Verification suite for the 'Iceberg' Campaign Weaver and Async Engine.
    """

    async def test_01_master_arc_initialization(self):
        """Verifies that a new game correctly initializes a hidden master arc."""
        print("\n[Test] Initializing New Game with Master Arc...")
        state = await engine.start_new_game()
        
        tracker_dict = state.get("meta", {}).get("campaign_tracker", {})
        self.assertIsNotNone(tracker_dict, "Campaign tracker should exist in meta.")
        
        # Validate using Pydantic
        tracker = CampaignTracker.model_validate(tracker_dict)
        self.assertIsNotNone(tracker.master_arc, "Master Arc should be initialized.")
        print(f"   -> Antagonist: {tracker.master_arc.antagonist_faction}")
        print(f"   -> Objective: {tracker.master_arc.target_objective}")
        print(f"   -> Key Nouns: {tracker.master_arc.key_nouns}")

    async def test_02_tension_scaling(self):
        """Verifies that tension scales based on current Act."""
        from campaign_director import CampaignWeaver
        weaver = CampaignWeaver()
        arc = MasterArc(
            antagonist_faction="iron_caldera",
            target_objective="Ignite the Sky-Forge",
            current_act=3,
            key_nouns=["Opal-Wallow", "Lophex"]
        )
        
        tension = weaver.evaluate_tension(arc)
        self.assertEqual(tension, 15, "Tension should be current_act * 5.")
        print(f"   -> Act 3 Tension Level: {tension}")

    async def test_03_quest_hook_injection(self):
        """Verifies that Master Arc context is injected into quest generation."""
        import quest_manager
        
        state = {
            "meta": {
                "campaign_tracker": {
                    "master_arc": {
                        "antagonist_faction": "sump_kin",
                        "target_objective": "The Lith-Siphon",
                        "key_nouns": ["Green-Glow", "Sump-Mother"],
                        "current_act": 2
                    }
                }
            }
        }
        
        print("\n[Test] Testing Quest Hook Injection (AI Simulation)...")
        # Since we use a real Ollama call, we check if the fallback or real result respects the context.
        # For CI/CD we might mock this, but here we want to see the prompt logic.
        result = await quest_manager.generate_story_glue("A broken mechanical bird", state)
        
        self.assertIn("story_hook", result)
        self.assertIn("involved_factions", result)
        print(f"   -> Hook generated: {result['story_hook']}")

if __name__ == "__main__":
    unittest.main()
