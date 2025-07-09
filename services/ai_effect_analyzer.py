"""
AI-powered video effect analyzer using LLMs for intelligent effect detection
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import openai
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class EffectMoment:
    """Represents a moment in the video where an effect should be applied"""
    start_time: float
    end_time: float
    effect_type: str
    intensity: float
    description: str
    confidence: float
    parameters: Dict[str, Any]

@dataclass
class AIAnalysisResult:
    """Result of AI analysis for video effects"""
    zoom_moments: List[EffectMoment]
    caption_moments: List[EffectMoment]
    overlay_moments: List[EffectMoment]
    transition_moments: List[EffectMoment]
    total_effects: int
    processing_complexity: str  # 'simple', 'moderate', 'complex'
    estimated_credits: int

class AIEffectAnalyzer:
    """AI-powered analyzer for determining video effects based on transcript"""
    
    def __init__(self):
        try:
            self.client = openai.OpenAI()
            self.use_mock = False
        except Exception:
            logger.warning("OpenAI not configured, using mock AI analysis")
            self.client = None
            self.use_mock = True
        
        # Effect type definitions
        self.effect_types = {
            'zoom': {
                'quick_pulse': 'Fast zoom in/out for excitement',
                'smooth_zoom_in': 'Gradual zoom for demonstrations',
                'emphasis_zoom': 'Strong zoom for important points',
                'gentle_zoom': 'Subtle zoom for questions',
                'dynamic_zoom': 'Energetic zoom for action',
                'professional_zoom': 'Business-style zoom for showcases'
            },
            'caption': {
                'highlight_text': 'Highlighted text overlay for key points',
                'animated_text': 'Animated text for excitement',
                'question_bubble': 'Speech bubble for questions',
                'emphasis_banner': 'Banner text for important info',
                'countdown_text': 'Countdown or numbered points',
                'quote_overlay': 'Quote-style text overlay'
            },
            'overlay': {
                'attention_arrow': 'Arrow pointing to important areas',
                'highlight_circle': 'Circle highlighting key elements',
                'emphasis_glow': 'Glow effect for special moments',
                'frame_border': 'Decorative frame for showcases',
                'progress_bar': 'Progress indicator for tutorials',
                'icon_overlay': 'Relevant icons for context'
            },
            'transition': {
                'quick_cut': 'Fast cut for energy',
                'smooth_fade': 'Gentle fade for transitions',
                'zoom_transition': 'Zoom-based scene change',
                'slide_transition': 'Sliding effect between points'
            }
        }
    
    async def analyze_transcript_for_effects(self, transcript: Dict[str, Any], video_duration: float) -> AIAnalysisResult:
        """Analyze transcript using AI to determine optimal video effects"""
        try:
            # Prepare transcript data for AI analysis
            segments = transcript.get('segments', [])
            full_text = transcript.get('text', '')
            
            if self.use_mock:
                # Use mock AI analysis for testing
                ai_response = self._create_mock_ai_response(segments, video_duration)
            else:
                # Create AI prompt for effect analysis
                analysis_prompt = self._create_analysis_prompt(segments, video_duration)

                # Get AI analysis
                ai_response = await self._query_ai_for_effects(analysis_prompt)

            # Parse AI response into effect moments
            analysis_result = self._parse_ai_response(ai_response, video_duration)
            
            logger.info(f"AI analysis complete: {analysis_result.total_effects} effects detected")
            return analysis_result
            
        except Exception as e:
            logger.error(f"AI effect analysis failed: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(transcript, video_duration)
    
    def _create_analysis_prompt(self, segments: List[Dict], video_duration: float) -> str:
        """Create a comprehensive prompt for AI effect analysis"""
        
        # Format segments for AI
        formatted_segments = []
        for segment in segments:
            formatted_segments.append({
                'start': round(segment.get('start', 0), 2),
                'end': round(segment.get('end', 0), 2),
                'text': segment.get('text', '').strip()
            })
        
        prompt = f"""
You are an expert video editor AI that analyzes video transcripts to determine optimal visual effects. 
Analyze the following transcript and suggest specific video effects with precise timing.

VIDEO DETAILS:
- Duration: {video_duration} seconds
- Type: Educational/Tutorial/Presentation content
- Target: Engaging social media and educational platforms

TRANSCRIPT SEGMENTS:
{json.dumps(formatted_segments, indent=2)}

EFFECT GUIDELINES:
1. ZOOM EFFECTS:
   - Use for emphasis, demonstrations, excitement
   - Duration: 0.5-3.0 seconds max
   - Types: quick_pulse, smooth_zoom_in, emphasis_zoom, gentle_zoom, dynamic_zoom, professional_zoom

2. CAPTION OVERLAYS:
   - Highlight key phrases, questions, important points
   - Duration: 1.0-5.0 seconds max
   - Types: highlight_text, animated_text, question_bubble, emphasis_banner, countdown_text, quote_overlay

3. VISUAL OVERLAYS:
   - Arrows, circles, highlights for demonstrations
   - Duration: 0.5-4.0 seconds max
   - Types: attention_arrow, highlight_circle, emphasis_glow, frame_border, progress_bar, icon_overlay

4. TRANSITIONS:
   - Between major topic changes
   - Duration: 0.2-1.0 seconds max
   - Types: quick_cut, smooth_fade, zoom_transition, slide_transition

CONSTRAINTS:
- Maximum 15 effects total (avoid over-processing)
- No overlapping effects of the same type
- Minimum 0.5 seconds between effects
- Focus on the most impactful moments
- Consider viewer attention span

RESPONSE FORMAT (JSON):
{{
  "zoom_effects": [
    {{
      "start_time": 10.5,
      "end_time": 12.0,
      "effect_type": "emphasis_zoom",
      "intensity": 0.8,
      "description": "Zoom in on important product feature",
      "confidence": 0.9,
      "trigger_phrase": "this is crucial"
    }}
  ],
  "caption_effects": [
    {{
      "start_time": 15.2,
      "end_time": 18.0,
      "effect_type": "highlight_text",
      "intensity": 0.7,
      "description": "Highlight key benefit",
      "confidence": 0.85,
      "text_content": "50% faster results",
      "position": "center"
    }}
  ],
  "overlay_effects": [
    {{
      "start_time": 25.0,
      "end_time": 27.5,
      "effect_type": "attention_arrow",
      "intensity": 0.6,
      "description": "Point to demonstration area",
      "confidence": 0.8,
      "position": "bottom_right"
    }}
  ],
  "transition_effects": [
    {{
      "start_time": 30.0,
      "end_time": 30.5,
      "effect_type": "smooth_fade",
      "intensity": 0.5,
      "description": "Transition to next topic",
      "confidence": 0.7
    }}
  ],
  "complexity": "moderate",
  "reasoning": "Video contains clear demonstration moments and emphasis points suitable for enhancement"
}}

Analyze the transcript and provide intelligent effect suggestions that will enhance viewer engagement without overwhelming the content.
"""
        return prompt
    
    async def _query_ai_for_effects(self, prompt: str) -> Dict[str, Any]:
        """Query AI service for effect analysis"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert video editor AI. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"AI query failed: {e}")
            raise

    def _create_mock_ai_response(self, segments: List[Dict], video_duration: float) -> Dict[str, Any]:
        """Create mock AI response for testing"""
        logger.info("Using mock AI analysis for testing")

        # Create some realistic mock effects based on video duration
        zoom_effects = []
        caption_effects = []
        overlay_effects = []
        transition_effects = []

        # Add zoom effects at key moments
        if segments and len(segments) > 0:
            # Add zoom at the beginning
            first_segment = segments[0]
            zoom_effects.append({
                "start_time": first_segment.get('start', 0),
                "end_time": min(first_segment.get('end', 2), first_segment.get('start', 0) + 2),
                "effect_type": "professional_zoom",
                "intensity": 0.7,
                "description": "Opening emphasis zoom",
                "confidence": 0.8,
                "trigger_phrase": first_segment.get('text', '')[:20]
            })

            # Add zoom in the middle if video is long enough
            if video_duration > 60:
                mid_time = video_duration / 2
                zoom_effects.append({
                    "start_time": mid_time,
                    "end_time": mid_time + 1.5,
                    "effect_type": "emphasis_zoom",
                    "intensity": 0.8,
                    "description": "Mid-video emphasis",
                    "confidence": 0.7,
                    "trigger_phrase": "key point"
                })

        # Add caption effects
        if len(segments) > 2:
            # Add caption for an important segment
            important_segment = segments[min(2, len(segments) - 1)]
            caption_effects.append({
                "start_time": important_segment.get('start', 10),
                "end_time": important_segment.get('end', 15),
                "effect_type": "highlight_text",
                "intensity": 0.6,
                "description": "Highlight key information",
                "confidence": 0.75,
                "text_content": "Key Point",
                "position": "center"
            })

        # Add overlay effect
        if video_duration > 30:
            overlay_effects.append({
                "start_time": 20.0,
                "end_time": 22.5,
                "effect_type": "attention_arrow",
                "intensity": 0.6,
                "description": "Point to important area",
                "confidence": 0.7,
                "position": "bottom_right"
            })

        # Determine complexity based on video duration and effects
        total_effects = len(zoom_effects) + len(caption_effects) + len(overlay_effects)
        if total_effects <= 2:
            complexity = "simple"
        elif total_effects <= 4:
            complexity = "moderate"
        else:
            complexity = "complex"

        return {
            "zoom_effects": zoom_effects,
            "caption_effects": caption_effects,
            "overlay_effects": overlay_effects,
            "transition_effects": transition_effects,
            "complexity": complexity,
            "reasoning": f"Mock analysis generated {total_effects} effects for {video_duration:.1f}s video"
        }
    
    def _parse_ai_response(self, ai_response: Dict[str, Any], video_duration: float) -> AIAnalysisResult:
        """Parse AI response into structured effect moments"""
        
        zoom_moments = []
        caption_moments = []
        overlay_moments = []
        transition_moments = []
        
        # Parse zoom effects
        for effect in ai_response.get('zoom_effects', []):
            zoom_moments.append(EffectMoment(
                start_time=effect['start_time'],
                end_time=effect['end_time'],
                effect_type=effect['effect_type'],
                intensity=effect['intensity'],
                description=effect['description'],
                confidence=effect['confidence'],
                parameters={'trigger_phrase': effect.get('trigger_phrase', '')}
            ))
        
        # Parse caption effects
        for effect in ai_response.get('caption_effects', []):
            caption_moments.append(EffectMoment(
                start_time=effect['start_time'],
                end_time=effect['end_time'],
                effect_type=effect['effect_type'],
                intensity=effect['intensity'],
                description=effect['description'],
                confidence=effect['confidence'],
                parameters={
                    'text_content': effect.get('text_content', ''),
                    'position': effect.get('position', 'center')
                }
            ))
        
        # Parse overlay effects
        for effect in ai_response.get('overlay_effects', []):
            overlay_moments.append(EffectMoment(
                start_time=effect['start_time'],
                end_time=effect['end_time'],
                effect_type=effect['effect_type'],
                intensity=effect['intensity'],
                description=effect['description'],
                confidence=effect['confidence'],
                parameters={'position': effect.get('position', 'center')}
            ))
        
        # Parse transition effects
        for effect in ai_response.get('transition_effects', []):
            transition_moments.append(EffectMoment(
                start_time=effect['start_time'],
                end_time=effect['end_time'],
                effect_type=effect['effect_type'],
                intensity=effect['intensity'],
                description=effect['description'],
                confidence=effect['confidence'],
                parameters={}
            ))
        
        total_effects = len(zoom_moments) + len(caption_moments) + len(overlay_moments) + len(transition_moments)
        complexity = ai_response.get('complexity', 'moderate')
        
        # Calculate estimated credits (100 credits per minute base + complexity multiplier)
        base_credits = int(video_duration / 60 * 100)
        complexity_multiplier = {'simple': 1.0, 'moderate': 1.2, 'complex': 1.5}.get(complexity, 1.2)
        estimated_credits = int(base_credits * complexity_multiplier)
        
        return AIAnalysisResult(
            zoom_moments=zoom_moments,
            caption_moments=caption_moments,
            overlay_moments=overlay_moments,
            transition_moments=transition_moments,
            total_effects=total_effects,
            processing_complexity=complexity,
            estimated_credits=estimated_credits
        )
    
    def _create_fallback_analysis(self, transcript: Dict[str, Any], video_duration: float) -> AIAnalysisResult:
        """Create fallback analysis if AI fails"""
        logger.warning("Using fallback effect analysis")
        
        # Simple fallback: basic zoom on first and last segments
        segments = transcript.get('segments', [])
        zoom_moments = []
        
        if segments:
            # Add zoom to first segment
            first_segment = segments[0]
            zoom_moments.append(EffectMoment(
                start_time=first_segment.get('start', 0),
                end_time=min(first_segment.get('end', 2), first_segment.get('start', 0) + 2),
                effect_type='professional_zoom',
                intensity=0.6,
                description='Opening zoom effect',
                confidence=0.5,
                parameters={}
            ))
        
        base_credits = int(video_duration / 60 * 100)
        
        return AIAnalysisResult(
            zoom_moments=zoom_moments,
            caption_moments=[],
            overlay_moments=[],
            transition_moments=[],
            total_effects=len(zoom_moments),
            processing_complexity='simple',
            estimated_credits=base_credits
        )
