import random
import re
from typing import Dict, List, Tuple, Optional

class DiceRoller:
    def __init__(self):
        self.dice_pattern = re.compile(r'(\d+)d(\d+)(?:\s*([-+])\s*(\d+))?(?:\s+(adv|dis))?')

    def execute_roll(self, roll_string: str) -> dict:
        """Execute a dice roll with modifiers"""
        try:
            roll_string = roll_string.lower().strip()
            match = self.dice_pattern.match(roll_string)
            
            if not match:
                return {
                    'success': False,
                    'error': 'Invalid roll format. Use: "XdY+Z" (e.g., 1d20+4, 2d6-1)'
                }
            
            num_dice = int(match.group(1))
            dice_type = int(match.group(2))
            modifier_sign = match.group(3) or ''
            modifier_value = int(match.group(4) or 0)
            advantage_type = match.group(5) if len(match.groups()) > 4 else None
            
            # Validate dice numbers
            if num_dice > 100 or dice_type > 100:
                return {
                    'success': False,
                    'error': 'Too many dice or sides (max 100)'
                }
            
            rolls = []
            details = []
            
            # Handle advantage/disadvantage
            if advantage_type in ['adv', 'dis']:
                roll1 = [random.randint(1, dice_type) for _ in range(num_dice)]
                roll2 = [random.randint(1, dice_type) for _ in range(num_dice)]
                
                if advantage_type == 'adv':
                    rolls = [max(r1, r2) for r1, r2 in zip(roll1, roll2)]
                    details.append({
                        'dice': f'{num_dice}d{dice_type}',
                        'rolls': [roll1, roll2],
                        'advantage': True,
                        'subtotal': sum(rolls)
                    })
                else:
                    rolls = [min(r1, r2) for r1, r2 in zip(roll1, roll2)]
                    details.append({
                        'dice': f'{num_dice}d{dice_type}',
                        'rolls': [roll1, roll2],
                        'disadvantage': True,
                        'subtotal': sum(rolls)
                    })
            else:
                # Regular roll
                rolls = [random.randint(1, dice_type) for _ in range(num_dice)]
                details.append({
                    'dice': f'{num_dice}d{dice_type}',
                    'rolls': rolls,
                    'subtotal': sum(rolls)
                })
            
            # Apply modifier
            total = sum(rolls)
            if modifier_sign and modifier_value:
                if modifier_sign == '+':
                    total += modifier_value
                else:
                    total -= modifier_value
                details.append({
                    'dice': f'{modifier_sign}{modifier_value}',
                    'rolls': [modifier_value],
                    'subtotal': modifier_value
                })
            
            return {
                'success': True,
                'total': total,
                'details': details,
                'rolls': rolls,
                'modifier': f'{modifier_sign}{modifier_value}' if modifier_sign else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }