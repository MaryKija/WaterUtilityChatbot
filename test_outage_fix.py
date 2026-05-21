#!/usr/bin/env python3
"""Test script for improved outage handling logic."""

import asyncio
from backend.orchestrator import ComplaintAgent

async def test_outage_flow():
    agent = ComplaintAgent()
    
    # Test case: User wants outage information with area
    print('=== Test: User wants outage info ===')
    context = {'intent': 'water_outage', 'entities': {'area': 'Kabwe'}}
    result = await agent.handle('I want an update about a water outage', context)
    print('Result:', result['reply'])
    
    # Test case: User wants outage information without area
    print('\n=== Test: User wants outage info without area ===')
    context2 = {'intent': 'water_outage', 'entities': {}}
    result2 = await agent.handle('I want an update about a water outage', context2)
    print('Result:', result2['reply'])

if __name__ == "__main__":
    asyncio.run(test_outage_flow())
