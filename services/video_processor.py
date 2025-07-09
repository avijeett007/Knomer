"""
Comprehensive video processing service with advanced features
"""
import os
import subprocess
import tempfile
import logging
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import whisper
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config.settings import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Advanced video processing service with AI features"""
    
    def __init__(self):
        # Load Whisper model for transcription
        self.whisper_model = None
        self._load_whisper_model()
        
        # Emoji mappings for sentiment and keywords
        self.emoji_mappings = {
            'happy': ['😊', '😄', '🎉', '👍', '❤️'],
            'sad': ['😢', '😞', '💔', '😔'],
            'excited': ['🎉', '🚀', '⭐', '🔥', '💫'],
            'love': ['❤️', '💕', '😍', '💖', '💝'],
            'food': ['🍕', '🍔', '🍰', '🥗', '🍜'],
            'travel': ['✈️', '🌍', '🗺️', '🏖️', '🏔️'],
            'music': ['🎵', '🎶', '🎤', '🎸', '🎹'],
            'sports': ['⚽', '🏀', '🎾', '🏈', '⚾'],
            'work': ['💼', '💻', '📊', '📈', '🎯'],
            'celebration': ['🎊', '🎈', '🥳', '🍾', '🎁']
        }
        
        # Enhanced keywords for dynamic auto-zoom detection
        self.zoom_keywords = {
            # High-energy expressions (quick zoom in/out)
            'excitement': [
                'wow', 'amazing', 'incredible', 'awesome', 'fantastic', 'unbelievable',
                'mind-blowing', 'spectacular', 'extraordinary', 'phenomenal', 'stunning',
                'brilliant', 'excellent', 'perfect', 'outstanding', 'remarkable'
            ],

            # Emphasis words (strong zoom in)
            'emphasis': [
                'important', 'crucial', 'key', 'essential', 'vital', 'critical',
                'main', 'primary', 'focus', 'highlight', 'remember', 'note',
                'pay attention', 'listen', 'watch', 'look', 'see this'
            ],

            # Tutorial/demonstration (smooth zoom in)
            'demonstration': [
                'show you', 'demonstrate', 'example', 'here', 'this is',
                'look at', 'check out', 'see how', 'watch this', 'observe',
                'notice', 'step', 'process', 'method', 'technique'
            ],

            # Emotional expressions (pulse zoom)
            'emotional': [
                'love', 'hate', 'excited', 'surprised', 'shocked', 'disappointed',
                'happy', 'sad', 'angry', 'frustrated', 'thrilled', 'delighted',
                'worried', 'concerned', 'relieved', 'grateful'
            ],

            # Questions/curiosity (gentle zoom)
            'curiosity': [
                'what', 'how', 'why', 'when', 'where', 'question', 'wonder',
                'curious', 'interesting', 'strange', 'weird', 'unusual'
            ],

            # Action words (dynamic zoom)
            'action': [
                'action', 'movement', 'running', 'jumping', 'dancing', 'moving',
                'fast', 'quick', 'rapid', 'sudden', 'instant', 'immediately'
            ],

            # Product showcase (professional zoom)
            'showcase': [
                'product', 'item', 'feature', 'benefit', 'advantage', 'quality',
                'design', 'build', 'made', 'created', 'developed', 'innovative'
            ]
        }

        # Zoom effect patterns for different content types
        self.zoom_patterns = {
            'excitement': {
                'type': 'quick_pulse',
                'zoom_in': 1.8,
                'zoom_out': 1.0,
                'speed': 'fast',
                'duration_multiplier': 0.8
            },
            'emphasis': {
                'type': 'strong_zoom_in',
                'zoom_in': 2.0,
                'zoom_out': 1.2,
                'speed': 'medium',
                'duration_multiplier': 1.0
            },
            'demonstration': {
                'type': 'smooth_zoom_in',
                'zoom_in': 1.5,
                'zoom_out': 1.0,
                'speed': 'slow',
                'duration_multiplier': 1.2
            },
            'emotional': {
                'type': 'pulse_zoom',
                'zoom_in': 1.6,
                'zoom_out': 1.0,
                'speed': 'medium',
                'duration_multiplier': 1.0
            },
            'curiosity': {
                'type': 'gentle_zoom',
                'zoom_in': 1.3,
                'zoom_out': 1.0,
                'speed': 'slow',
                'duration_multiplier': 1.1
            },
            'action': {
                'type': 'dynamic_zoom',
                'zoom_in': 1.7,
                'zoom_out': 0.9,
                'speed': 'fast',
                'duration_multiplier': 0.9
            },
            'showcase': {
                'type': 'professional_zoom',
                'zoom_in': 1.4,
                'zoom_out': 1.0,
                'speed': 'medium',
                'duration_multiplier': 1.0
            }
        }
    
    def _load_whisper_model(self):
        """Load Whisper model for transcription"""
        try:
            # Temporarily disable Whisper to test audio separation
            logger.info("Whisper model loading disabled for testing")
            self.whisper_model = None
            # self.whisper_model = whisper.load_model("small")
            # logger.info("Whisper small model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
    
    def simple_merge(self, input_files: List[Path], output_path: Path) -> Dict[str, Any]:
        """Simple video concatenation without transitions"""
        try:
            # Create concat file for ffmpeg
            concat_file = output_path.parent / f"concat_{output_path.stem}.txt"
            
            with open(concat_file, 'w') as f:
                for video_file in input_files:
                    f.write(f"file '{video_file.absolute()}'\n")
            
            # FFmpeg command for simple concatenation
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            # Cleanup
            if concat_file.exists():
                concat_file.unlink()
            
            if result.returncode == 0:
                output_info = self._get_video_info(output_path)
                return {
                    'success': True,
                    'output_duration': output_info.get('duration', 0),
                    'output_size': output_path.stat().st_size if output_path.exists() else 0
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            logger.error(f"Error in simple merge: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def merge_with_transitions(
        self, 
        input_files: List[Path], 
        output_path: Path, 
        transitions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge videos with transition effects"""
        try:
            temp_dir = output_path.parent / f"temp_{output_path.stem}"
            temp_dir.mkdir(exist_ok=True)
            
            processed_videos = []
            
            # Process each video with transitions
            for i, video_file in enumerate(input_files):
                if i < len(transitions):
                    transition = transitions[i]
                    processed_video = self._apply_transition(
                        video_file, 
                        input_files[i + 1] if i + 1 < len(input_files) else None,
                        transition,
                        temp_dir / f"transition_{i}.mp4"
                    )
                    processed_videos.append(processed_video)
                else:
                    processed_videos.append(video_file)
            
            # Concatenate processed videos
            result = self.simple_merge(processed_videos, output_path)
            
            # Cleanup temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in transition merge: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _apply_transition(
        self, 
        video1: Path, 
        video2: Optional[Path], 
        transition: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """Apply transition effect between two videos"""
        try:
            transition_type = transition.get('type', 'fade')
            duration = transition.get('duration', 1.0)
            
            if not video2:
                # No second video, just return first video
                return video1
            
            # Get video durations
            info1 = self._get_video_info(video1)
            info2 = self._get_video_info(video2)
            
            if transition_type == 'fade':
                filter_complex = f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={info1['duration']-duration}[v]"
            elif transition_type == 'dissolve':
                filter_complex = f"[0:v][1:v]xfade=transition=dissolve:duration={duration}:offset={info1['duration']-duration}[v]"
            elif transition_type == 'slide':
                filter_complex = f"[0:v][1:v]xfade=transition=slideleft:duration={duration}:offset={info1['duration']-duration}[v]"
            elif transition_type == 'zoom':
                filter_complex = f"[0:v][1:v]xfade=transition=zoomin:duration={duration}:offset={info1['duration']-duration}[v]"
            else:
                # Default to fade
                filter_complex = f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={info1['duration']-duration}[v]"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1),
                '-i', str(video2),
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-map', '0:a',
                '-c:a', 'copy',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                return output_path
            else:
                logger.error(f"Transition failed: {result.stderr}")
                return video1
                
        except Exception as e:
            logger.error(f"Error applying transition: {e}")
            return video1
    
    def apply_auto_effects(
        self, 
        input_files: List[Path], 
        output_path: Path, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply AI-powered auto effects based on content analysis"""
        try:
            # First, merge videos if multiple
            if len(input_files) > 1:
                merged_video = output_path.parent / f"merged_{output_path.stem}.mp4"
                merge_result = self.simple_merge(input_files, merged_video)
                if not merge_result['success']:
                    return merge_result
                working_video = merged_video
            else:
                working_video = input_files[0]
            
            # Transcribe audio if enabled
            transcript = None
            if options.get('enable_transcription') and self.whisper_model:
                transcript = self._transcribe_video(working_video)
            
            # Apply effects based on transcript and options
            effects_applied = []
            current_video = working_video
            
            # Auto-zoom based on keywords
            if options.get('ai_effects_based_on_transcript') and transcript:
                zoom_video = self._apply_auto_zoom(current_video, transcript, output_path.parent / f"zoom_{output_path.stem}.mp4")
                if zoom_video != current_video:
                    current_video = zoom_video
                    effects_applied.append('auto_zoom')
            
            # Auto-resize for platform
            platform = options.get('platform', 'youtube')
            if platform == 'tiktok':
                resized_video = self._resize_for_tiktok(current_video, output_path.parent / f"resized_{output_path.stem}.mp4")
                if resized_video != current_video:
                    current_video = resized_video
                    effects_applied.append('tiktok_resize')
            
            # Add emojis based on transcript
            if transcript and options.get('ai_effects_based_on_transcript'):
                emoji_video = self._add_emojis_from_transcript(current_video, transcript, output_path)
                if emoji_video != current_video:
                    current_video = emoji_video
                    effects_applied.append('emoji_overlay')
            
            # Copy final result to output path if not already there
            if current_video != output_path:
                import shutil
                shutil.copy2(current_video, output_path)
            
            output_info = self._get_video_info(output_path)
            return {
                'success': True,
                'output_duration': output_info.get('duration', 0),
                'output_size': output_path.stat().st_size if output_path.exists() else 0,
                'effects_applied': effects_applied,
                'transcript': transcript
            }
            
        except Exception as e:
            logger.error(f"Error in auto effects: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_video(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """Transcribe video audio using Whisper"""
        try:
            if not self.whisper_model:
                return None
            
            # Extract audio from video
            audio_path = video_path.parent / f"audio_{video_path.stem}.wav"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Audio extraction failed: {result.stderr}")
                return None
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(str(audio_path))
            
            # Cleanup audio file
            if audio_path.exists():
                audio_path.unlink()
            
            return {
                'text': result['text'],
                'segments': result['segments'],
                'language': result['language']
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def _apply_auto_zoom(self, video_path: Path, transcript: Dict[str, Any], output_path: Path) -> Path:
        """Apply dynamic auto-zoom effects based on transcript analysis"""
        try:
            segments = transcript.get('segments', [])

            # Analyze segments for zoom moments with different patterns
            zoom_moments = self._analyze_zoom_moments(segments)

            if not zoom_moments:
                logger.info("No zoom moments detected in transcript")
                return video_path

            logger.info(f"Detected {len(zoom_moments)} zoom moments")

            # Create dynamic zoom filter
            zoom_filter = self._create_dynamic_zoom_filter(zoom_moments)

            if not zoom_filter:
                return video_path

            # Apply zoom effects
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vf', zoom_filter,
                '-c:a', 'copy',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                logger.info(f"Dynamic auto-zoom applied successfully")
                return output_path
            else:
                logger.error(f"Auto-zoom failed: {result.stderr}")
                return video_path

        except Exception as e:
            logger.error(f"Auto-zoom error: {e}")
            return video_path

    def _analyze_zoom_moments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze transcript segments to identify zoom moments with appropriate patterns"""
        zoom_moments = []

        for segment in segments:
            segment_text = segment.get('text', '').lower()
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            duration = end_time - start_time

            # Skip very short segments
            if duration < 0.5:
                continue

            # Find the best matching zoom category
            zoom_category = self._detect_zoom_category(segment_text)

            if zoom_category:
                pattern = self.zoom_patterns[zoom_category]

                # Adjust timing based on pattern
                adjusted_duration = duration * pattern['duration_multiplier']
                adjusted_end = start_time + min(adjusted_duration, duration)

                zoom_moments.append({
                    'start': start_time,
                    'end': adjusted_end,
                    'original_end': end_time,
                    'text': segment_text,
                    'category': zoom_category,
                    'pattern': pattern,
                    'intensity': self._calculate_zoom_intensity(segment_text, zoom_category)
                })

                logger.info(f"Zoom moment: '{segment_text[:50]}...' -> {zoom_category} ({start_time:.1f}s-{adjusted_end:.1f}s)")

        return zoom_moments

    def _detect_zoom_category(self, text: str) -> Optional[str]:
        """Detect the most appropriate zoom category for the given text"""
        # Score each category based on keyword matches
        category_scores = {}

        for category, keywords in self.zoom_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    # Give higher score for exact matches and longer keywords
                    score += len(keyword.split()) * 2
                    # Bonus for exclamation-like words
                    if keyword in ['wow', 'amazing', 'incredible', 'awesome']:
                        score += 3

            if score > 0:
                category_scores[category] = score

        # Return the category with the highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)

        return None

    def _calculate_zoom_intensity(self, text: str, category: str) -> float:
        """Calculate zoom intensity based on text analysis"""
        base_intensity = 1.0

        # Increase intensity for exclamation marks
        exclamation_count = text.count('!')
        base_intensity += exclamation_count * 0.2

        # Increase intensity for capital letters (shouting)
        if any(word.isupper() for word in text.split()):
            base_intensity += 0.3

        # Increase intensity for multiple emphasis words
        emphasis_words = ['very', 'really', 'extremely', 'super', 'ultra', 'mega']
        for word in emphasis_words:
            if word in text:
                base_intensity += 0.15

        # Category-specific adjustments
        if category == 'excitement':
            base_intensity += 0.4
        elif category == 'emphasis':
            base_intensity += 0.3
        elif category == 'emotional':
            base_intensity += 0.2

        # Cap the intensity
        return min(base_intensity, 2.0)

    def _create_dynamic_zoom_filter(self, zoom_moments: List[Dict[str, Any]]) -> str:
        """Create a complex FFmpeg filter for dynamic zoom effects"""
        if not zoom_moments:
            return ""

        # Build the zoom expression
        zoom_expressions = []

        for moment in zoom_moments:
            start = moment['start']
            end = moment['end']
            pattern = moment['pattern']
            intensity = moment['intensity']
            category = moment['category']

            # Calculate zoom values with intensity
            zoom_in = pattern['zoom_in'] * intensity
            zoom_out = pattern['zoom_out']

            # Create different zoom patterns based on type
            if pattern['type'] == 'quick_pulse':
                # Quick zoom in and out (for excitement)
                mid_point = start + (end - start) * 0.3
                zoom_expr = f"if(between(t,{start},{mid_point}),1+({zoom_in}-1)*((t-{start})/({mid_point}-{start})),if(between(t,{mid_point},{end}),{zoom_in}-(({zoom_in}-{zoom_out})*((t-{mid_point})/({end}-{mid_point}))),1))"

            elif pattern['type'] == 'strong_zoom_in':
                # Strong zoom in and hold (for emphasis)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*min(1,(t-{start})*2),1)"

            elif pattern['type'] == 'smooth_zoom_in':
                # Smooth zoom in (for demonstrations)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*((t-{start})/({end}-{start})),1)"

            elif pattern['type'] == 'pulse_zoom':
                # Pulsing zoom (for emotions)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*abs(sin(2*PI*(t-{start})*2)),1)"

            elif pattern['type'] == 'gentle_zoom':
                # Gentle zoom (for curiosity)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*sin(PI*(t-{start})/({end}-{start})),1)"

            elif pattern['type'] == 'dynamic_zoom':
                # Dynamic zoom with movement (for action)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*sin(PI*(t-{start})*3),1)"

            elif pattern['type'] == 'professional_zoom':
                # Professional smooth zoom (for showcase)
                zoom_expr = f"if(between(t,{start},{end}),1+({zoom_in}-1)*((t-{start})/({end}-{start}))^0.5,1)"

            else:
                # Default zoom
                zoom_expr = f"if(between(t,{start},{end}),{zoom_in},1)"

            zoom_expressions.append(zoom_expr)

        # Combine all zoom expressions
        if len(zoom_expressions) == 1:
            final_zoom = zoom_expressions[0]
        else:
            # Multiply all zoom expressions (they should be 1 when not active)
            final_zoom = '*'.join(f"({expr})" for expr in zoom_expressions)

        # Create the complete filter
        zoom_filter = f"zoompan=z='{final_zoom}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

        return zoom_filter

    def _resize_for_tiktok(self, video_path: Path, output_path: Path) -> Path:
        """Resize video for TikTok (9:16 aspect ratio)"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vf', 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280',
                '-c:a', 'copy',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                return output_path
            else:
                logger.error(f"TikTok resize failed: {result.stderr}")
                return video_path

        except Exception as e:
            logger.error(f"TikTok resize error: {e}")
            return video_path

    def _add_emojis_from_transcript(self, video_path: Path, transcript: Dict[str, Any], output_path: Path) -> Path:
        """Add emojis based on transcript sentiment and keywords"""
        try:
            segments = transcript.get('segments', [])

            # Analyze segments for emoji placement
            emoji_overlays = []
            for segment in segments:
                segment_text = segment.get('text', '').lower()
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)

                # Find appropriate emoji
                emoji = self._select_emoji_for_text(segment_text)
                if emoji:
                    emoji_overlays.append({
                        'emoji': emoji,
                        'start': start_time,
                        'end': end_time,
                        'position': self._get_random_emoji_position()
                    })

            if not emoji_overlays:
                return video_path

            # Create emoji overlay video
            return self._apply_emoji_overlays(video_path, emoji_overlays, output_path)

        except Exception as e:
            logger.error(f"Emoji overlay error: {e}")
            return video_path

    def _select_emoji_for_text(self, text: str) -> Optional[str]:
        """Select appropriate emoji based on text content"""
        import random

        # Check for sentiment and keyword matches
        for category, emojis in self.emoji_mappings.items():
            if category in text or any(word in text for word in [
                'good', 'great', 'awesome', 'amazing', 'love', 'like',
                'happy', 'excited', 'wonderful', 'fantastic'
            ] if category == 'happy'):
                return random.choice(emojis)

        # Default emoji for general positive sentiment
        if any(word in text for word in ['good', 'nice', 'great', 'cool']):
            return random.choice(['😊', '👍', '✨'])

        return None

    def _get_random_emoji_position(self) -> Dict[str, int]:
        """Get random position for emoji placement"""
        import random

        positions = [
            {'x': 50, 'y': 50},    # Top-left
            {'x': 850, 'y': 50},   # Top-right
            {'x': 50, 'y': 450},   # Bottom-left
            {'x': 850, 'y': 450},  # Bottom-right
            {'x': 450, 'y': 50},   # Top-center
        ]

        return random.choice(positions)

    def _apply_emoji_overlays(self, video_path: Path, emoji_overlays: List[Dict[str, Any]], output_path: Path) -> Path:
        """Apply emoji overlays to video"""
        try:
            # Create emoji images
            emoji_files = []
            temp_dir = video_path.parent / "emoji_temp"
            temp_dir.mkdir(exist_ok=True)

            for i, overlay in enumerate(emoji_overlays):
                emoji_file = self._create_emoji_image(overlay['emoji'], temp_dir / f"emoji_{i}.png")
                if emoji_file:
                    emoji_files.append((emoji_file, overlay))

            if not emoji_files:
                return video_path

            # Build filter complex for overlays
            filter_parts = []
            input_parts = ['-i', str(video_path)]

            for i, (emoji_file, overlay) in enumerate(emoji_files):
                input_parts.extend(['-i', str(emoji_file)])

                start = overlay['start']
                end = overlay['end']
                x = overlay['position']['x']
                y = overlay['position']['y']

                filter_parts.append(f"[{i+1}:v]scale=60:60[emoji{i}]")
                if i == 0:
                    filter_parts.append(f"[0:v][emoji{i}]overlay={x}:{y}:enable='between(t,{start},{end})'[v{i}]")
                else:
                    filter_parts.append(f"[v{i-1}][emoji{i}]overlay={x}:{y}:enable='between(t,{start},{end})'[v{i}]")

            filter_complex = ';'.join(filter_parts)
            final_output = f"[v{len(emoji_files)-1}]" if emoji_files else "[0:v]"

            cmd = [
                'ffmpeg', '-y'
            ] + input_parts + [
                '-filter_complex', filter_complex,
                '-map', final_output,
                '-map', '0:a',
                '-c:a', 'copy',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            # Cleanup
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            if result.returncode == 0:
                return output_path
            else:
                logger.error(f"Emoji overlay failed: {result.stderr}")
                return video_path

        except Exception as e:
            logger.error(f"Emoji overlay application error: {e}")
            return video_path

    def _create_emoji_image(self, emoji: str, output_path: Path) -> Optional[Path]:
        """Create an image file with emoji"""
        try:
            # Create image with emoji
            img = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # Try to use a font that supports emojis
            try:
                # On macOS
                font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 60)
            except:
                try:
                    # On Linux
                    font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 60)
                except:
                    # Fallback
                    font = ImageFont.load_default()

            # Draw emoji
            draw.text((20, 20), emoji, font=font, fill=(255, 255, 255, 255))

            # Save image
            img.save(output_path, 'PNG')
            return output_path

        except Exception as e:
            logger.error(f"Emoji image creation error: {e}")
            return None

    def add_logo_overlay(
        self,
        input_files: List[Path],
        output_path: Path,
        logo_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add logo watermark overlay to video"""
        try:
            # First, merge videos if multiple
            if len(input_files) > 1:
                merged_video = output_path.parent / f"merged_{output_path.stem}.mp4"
                merge_result = self.simple_merge(input_files, merged_video)
                if not merge_result['success']:
                    return merge_result
                working_video = merged_video
            else:
                working_video = input_files[0]

            logo_url = logo_config.get('logo_url')
            position = logo_config.get('position', 'top-right')
            size = logo_config.get('size', 0.1)
            opacity = logo_config.get('opacity', 1.0)

            # Download logo if it's a URL
            if logo_url.startswith('http'):
                logo_path = self._download_logo(logo_url, output_path.parent)
            else:
                logo_path = Path(logo_url)

            if not logo_path or not logo_path.exists():
                return {
                    'success': False,
                    'error': 'Logo file not found'
                }

            # Get video dimensions
            video_info = self._get_video_info(working_video)
            video_width = video_info.get('width', 1920)
            video_height = video_info.get('height', 1080)

            # Calculate logo size and position
            logo_width = int(video_width * size)
            logo_height = int(logo_width * 0.5)  # Maintain aspect ratio

            # Position mapping
            positions = {
                'top-left': f"10:10",
                'top-right': f"{video_width - logo_width - 10}:10",
                'bottom-left': f"10:{video_height - logo_height - 10}",
                'bottom-right': f"{video_width - logo_width - 10}:{video_height - logo_height - 10}",
                'center': f"{(video_width - logo_width) // 2}:{(video_height - logo_height) // 2}"
            }

            overlay_position = positions.get(position, positions['top-right'])

            # Apply logo overlay
            cmd = [
                'ffmpeg', '-y',
                '-i', str(working_video),
                '-i', str(logo_path),
                '-filter_complex',
                f"[1:v]scale={logo_width}:{logo_height}[logo];"
                f"[0:v][logo]overlay={overlay_position}:format=auto,format=yuv420p",
                '-c:a', 'copy',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                output_info = self._get_video_info(output_path)
                return {
                    'success': True,
                    'output_duration': output_info.get('duration', 0),
                    'output_size': output_path.stat().st_size if output_path.exists() else 0
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }

        except Exception as e:
            logger.error(f"Logo overlay error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def merge_multiple_videos(
        self,
        input_files: List[Path],
        output_path: Path,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge multiple videos with advanced options"""
        try:
            # Apply transitions if specified
            if options.get('transitions'):
                return self.merge_with_transitions(input_files, output_path, options['transitions'])
            else:
                return self.simple_merge(input_files, output_path)

        except Exception as e:
            logger.error(f"Multi-video merge error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _download_logo(self, logo_url: str, temp_dir: Path) -> Optional[Path]:
        """Download logo from URL"""
        try:
            import requests

            response = requests.get(logo_url, timeout=30)
            response.raise_for_status()

            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                ext = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            else:
                ext = '.png'  # Default

            logo_path = temp_dir / f"logo{ext}"

            with open(logo_path, 'wb') as f:
                f.write(response.content)

            return logo_path

        except Exception as e:
            logger.error(f"Logo download error: {e}")
            return None

    def _get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video information using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                info = json.loads(result.stdout)

                # Extract video stream info
                video_stream = None
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break

                format_info = info.get('format', {})

                return {
                    'duration': float(format_info.get('duration', 0)),
                    'size': int(format_info.get('size', 0)),
                    'width': int(video_stream.get('width', 0)) if video_stream else 0,
                    'height': int(video_stream.get('height', 0)) if video_stream else 0,
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0,
                    'codec': video_stream.get('codec_name', '') if video_stream else ''
                }
            else:
                logger.error(f"ffprobe failed: {result.stderr}")
                return {}

        except Exception as e:
            logger.error(f"Video info error: {e}")
            return {}

    def validate_video_file(self, video_path: Path) -> Dict[str, Any]:
        """Validate video file and return info"""
        try:
            if not video_path.exists():
                return {
                    'valid': False,
                    'error': 'File does not exist'
                }

            info = self._get_video_info(video_path)

            if not info or info.get('duration', 0) <= 0:
                return {
                    'valid': False,
                    'error': 'Invalid video file or no duration'
                }

            # Check file size limits
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.MAX_VIDEO_SIZE_MB:
                return {
                    'valid': False,
                    'error': f'File size ({file_size_mb:.1f}MB) exceeds limit ({settings.MAX_VIDEO_SIZE_MB}MB)'
                }

            # Check duration limits
            if info['duration'] > settings.MAX_VIDEO_DURATION_SECONDS:
                return {
                    'valid': False,
                    'error': f'Duration ({info["duration"]:.1f}s) exceeds limit ({settings.MAX_VIDEO_DURATION_SECONDS}s)'
                }

            return {
                'valid': True,
                'info': info
            }

        except Exception as e:
            logger.error(f"Video validation error: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
