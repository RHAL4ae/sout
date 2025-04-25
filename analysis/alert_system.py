from typing import Dict, Any

class AlertSystem:
    """
    Generate alerts for non-measurable metrics:
    - Emotional Expressions
    - Audience Reactions
    - Visual Dynamics
    """
    def __init__(self):
        self.alerts = []

    def analyze_qualitative(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        alerts = []
        if observations.get('emotional_expression', 0) < 0.5:
            alerts.append({'metric': 'emotional_expression', 'message': 'Low emotional expression detected'})
        if observations.get('audience_reaction', 0) < 0.5:
            alerts.append({'metric': 'audience_reaction', 'message': 'Weak audience reaction'})
        if observations.get('visual_dynamics', 0) < 0.5:
            alerts.append({'metric': 'visual_dynamics', 'message': 'Limited visual dynamics'})
        self.alerts = alerts
        return {'alerts': alerts}
