"""
Premium AI-powered video processor with step-by-step async processing and retry capability
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import time

from .ai_effect_analyzer import AIEffectAnalyzer, AIAnalysisResult, EffectMoment
from .video_processor import VideoProcessor

logger = logging.getLogger(__name__)

class ProcessingStep(Enum):
    """Processing steps for premium video enhancement"""
    INITIALIZATION = "initialization"
    TRANSCRIPTION = "transcription"
    AI_ANALYSIS = "ai_analysis"
    EFFECT_PLANNING = "effect_planning"
    ZOOM_EFFECTS = "zoom_effects"
    CAPTION_EFFECTS = "caption_effects"
    OVERLAY_EFFECTS = "overlay_effects"
    LOGO_OVERLAY = "logo_overlay"
    FINAL_ASSEMBLY = "final_assembly"
    CLEANUP = "cleanup"
    COMPLETED = "completed"

@dataclass
class ProcessingProgress:
    """Tracks processing progress for premium video enhancement"""
    job_id: str
    current_step: ProcessingStep
    completed_steps: List[ProcessingStep]
    failed_steps: List[ProcessingStep]
    step_outputs: Dict[str, str]  # step -> output file path
    progress_percentage: float
    estimated_credits: int
    actual_credits_used: int
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

class PremiumVideoProcessor:
    """Premium AI-powered video processor with granular step tracking"""
    
    def __init__(self):
        self.ai_analyzer = AIEffectAnalyzer()
        self.base_processor = VideoProcessor()
        self.temp_dir = Path("/tmp/premium_processing")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Processing step weights for progress calculation
        self.step_weights = {
            ProcessingStep.INITIALIZATION: 5,
            ProcessingStep.TRANSCRIPTION: 15,
            ProcessingStep.AI_ANALYSIS: 10,
            ProcessingStep.EFFECT_PLANNING: 5,
            ProcessingStep.ZOOM_EFFECTS: 20,
            ProcessingStep.CAPTION_EFFECTS: 15,
            ProcessingStep.OVERLAY_EFFECTS: 10,
            ProcessingStep.LOGO_OVERLAY: 10,
            ProcessingStep.FINAL_ASSEMBLY: 8,
            ProcessingStep.CLEANUP: 2
        }
    
    async def process_premium_video(
        self, 
        video_path: Path, 
        job_id: str,
        logo_path: Optional[Path] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessingProgress:
        """Process video with premium AI-powered effects"""
        
        progress = ProcessingProgress(
            job_id=job_id,
            current_step=ProcessingStep.INITIALIZATION,
            completed_steps=[],
            failed_steps=[],
            step_outputs={},
            progress_percentage=0.0,
            estimated_credits=0,
            actual_credits_used=0
        )
        
        try:
            # Step 1: Initialization
            await self._execute_step(
                progress, 
                ProcessingStep.INITIALIZATION,
                self._initialize_processing,
                video_path, job_id,
                progress_callback=progress_callback
            )
            
            # Step 2: Transcription
            await self._execute_step(
                progress,
                ProcessingStep.TRANSCRIPTION,
                self._transcribe_video,
                video_path,
                progress_callback=progress_callback
            )
            
            # Step 3: AI Analysis
            await self._execute_step(
                progress,
                ProcessingStep.AI_ANALYSIS,
                self._analyze_with_ai,
                progress.step_outputs[ProcessingStep.TRANSCRIPTION.value],
                video_path,
                progress_callback=progress_callback
            )
            
            # Step 4: Effect Planning
            await self._execute_step(
                progress,
                ProcessingStep.EFFECT_PLANNING,
                self._plan_effects,
                progress.step_outputs[ProcessingStep.AI_ANALYSIS.value],
                progress_callback=progress_callback
            )
            
            # Step 5: Apply Zoom Effects
            await self._execute_step(
                progress,
                ProcessingStep.ZOOM_EFFECTS,
                self._apply_zoom_effects,
                video_path,
                progress.step_outputs[ProcessingStep.EFFECT_PLANNING.value],
                progress_callback=progress_callback
            )
            
            # Step 6: Apply Caption Effects
            await self._execute_step(
                progress,
                ProcessingStep.CAPTION_EFFECTS,
                self._apply_caption_effects,
                progress.step_outputs[ProcessingStep.ZOOM_EFFECTS.value],
                progress.step_outputs[ProcessingStep.EFFECT_PLANNING.value],
                progress_callback=progress_callback
            )
            
            # Step 7: Apply Overlay Effects
            await self._execute_step(
                progress,
                ProcessingStep.OVERLAY_EFFECTS,
                self._apply_overlay_effects,
                progress.step_outputs[ProcessingStep.CAPTION_EFFECTS.value],
                progress.step_outputs[ProcessingStep.EFFECT_PLANNING.value],
                progress_callback=progress_callback
            )
            
            # Step 8: Logo Overlay (if provided)
            if logo_path:
                await self._execute_step(
                    progress,
                    ProcessingStep.LOGO_OVERLAY,
                    self._apply_logo_overlay,
                    progress.step_outputs[ProcessingStep.OVERLAY_EFFECTS.value],
                    logo_path,
                    progress_callback=progress_callback
                )
            else:
                # Skip logo step
                progress.step_outputs[ProcessingStep.LOGO_OVERLAY.value] = progress.step_outputs[ProcessingStep.OVERLAY_EFFECTS.value]
                progress.completed_steps.append(ProcessingStep.LOGO_OVERLAY)
            
            # Step 9: Final Assembly
            await self._execute_step(
                progress,
                ProcessingStep.FINAL_ASSEMBLY,
                self._final_assembly,
                progress.step_outputs[ProcessingStep.LOGO_OVERLAY.value],
                job_id,
                progress_callback=progress_callback
            )
            
            # Step 10: Cleanup
            await self._execute_step(
                progress,
                ProcessingStep.CLEANUP,
                self._cleanup_temp_files,
                job_id,
                progress_callback=progress_callback
            )
            
            progress.current_step = ProcessingStep.COMPLETED
            progress.progress_percentage = 100.0
            
            if progress_callback:
                await progress_callback(progress)
            
            logger.info(f"Premium processing completed for job {job_id}")
            return progress
            
        except Exception as e:
            progress.error_message = str(e)
            logger.error(f"Premium processing failed for job {job_id}: {e}")
            return progress
    
    async def _execute_step(
        self, 
        progress: ProcessingProgress, 
        step: ProcessingStep, 
        step_function: callable,
        *args,
        progress_callback: Optional[callable] = None
    ):
        """Execute a processing step with retry capability"""
        
        progress.current_step = step
        
        for attempt in range(progress.max_retries):
            try:
                logger.info(f"Executing step {step.value} (attempt {attempt + 1})")
                
                # Execute the step function
                result = await step_function(*args)
                
                # Store result
                if isinstance(result, (str, Path)):
                    progress.step_outputs[step.value] = str(result)
                elif isinstance(result, dict):
                    progress.step_outputs[step.value] = json.dumps(result)
                
                # Mark step as completed
                progress.completed_steps.append(step)
                
                # Update progress percentage
                completed_weight = sum(self.step_weights[s] for s in progress.completed_steps)
                total_weight = sum(self.step_weights.values())
                progress.progress_percentage = (completed_weight / total_weight) * 100
                
                # Call progress callback
                if progress_callback:
                    await progress_callback(progress)
                
                logger.info(f"Step {step.value} completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Step {step.value} failed (attempt {attempt + 1}): {e}")
                progress.retry_count = attempt + 1
                
                if attempt == progress.max_retries - 1:
                    # Final attempt failed
                    progress.failed_steps.append(step)
                    progress.error_message = f"Step {step.value} failed after {progress.max_retries} attempts: {e}"
                    raise
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _initialize_processing(self, video_path: Path, job_id: str) -> str:
        """Initialize processing environment"""
        job_temp_dir = self.temp_dir / job_id
        job_temp_dir.mkdir(exist_ok=True)
        
        # Get video info
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to analyze video: {result.stderr}")
        
        video_info = json.loads(result.stdout)
        duration = float(video_info['format']['duration'])
        
        # Save video info
        info_file = job_temp_dir / "video_info.json"
        with open(info_file, 'w') as f:
            json.dump({
                'duration': duration,
                'format': video_info['format'],
                'original_path': str(video_path)
            }, f)
        
        return str(info_file)
    
    async def _transcribe_video(self, video_path: Path) -> str:
        """Transcribe video using Whisper"""
        # Use existing transcription method
        transcript = self.base_processor._transcribe_video(video_path)
        
        # Save transcript
        transcript_file = self.temp_dir / f"transcript_{int(time.time())}.json"
        with open(transcript_file, 'w') as f:
            json.dump(transcript, f)
        
        return str(transcript_file)
    
    async def _analyze_with_ai(self, transcript_file: str, video_path: Path) -> str:
        """Analyze transcript with AI for effect suggestions"""
        # Load transcript
        with open(transcript_file, 'r') as f:
            transcript = json.load(f)
        
        # Get video duration
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # Analyze with AI
        analysis_result = await self.ai_analyzer.analyze_transcript_for_effects(transcript, duration)
        
        # Save analysis
        analysis_file = self.temp_dir / f"ai_analysis_{int(time.time())}.json"
        with open(analysis_file, 'w') as f:
            json.dump(asdict(analysis_result), f, default=str)
        
        return str(analysis_file)
    
    async def _plan_effects(self, analysis_file: str) -> str:
        """Plan effect application order and parameters"""
        # Load AI analysis
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        # Create effect plan
        effect_plan = {
            'zoom_effects': analysis_data.get('zoom_moments', []),
            'caption_effects': analysis_data.get('caption_moments', []),
            'overlay_effects': analysis_data.get('overlay_moments', []),
            'processing_order': ['zoom', 'caption', 'overlay', 'logo'],
            'estimated_credits': analysis_data.get('estimated_credits', 100)
        }
        
        # Save plan
        plan_file = self.temp_dir / f"effect_plan_{int(time.time())}.json"
        with open(plan_file, 'w') as f:
            json.dump(effect_plan, f)
        
        return str(plan_file)
    
    async def _apply_zoom_effects(self, video_path: Path, plan_file: str) -> str:
        """Apply AI-determined zoom effects"""
        # Load effect plan
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        zoom_effects = plan.get('zoom_effects', [])
        
        if not zoom_effects:
            # No zoom effects, return original
            return str(video_path)
        
        # Create zoom filter
        zoom_expressions = []
        for effect in zoom_effects:
            start = effect['start_time']
            end = effect['end_time']
            intensity = effect['intensity']
            effect_type = effect['effect_type']
            
            # Create zoom expression based on effect type
            if effect_type == 'quick_pulse':
                mid_point = start + (end - start) * 0.3
                zoom_expr = f"if(between(t,{start},{mid_point}),1+({1.5 * intensity}-1)*((t-{start})/({mid_point}-{start})),if(between(t,{mid_point},{end}),{1.5 * intensity}-(({1.5 * intensity}-1)*((t-{mid_point})/({end}-{mid_point}))),1))"
            elif effect_type == 'smooth_zoom_in':
                zoom_expr = f"if(between(t,{start},{end}),1+({1.3 * intensity}-1)*((t-{start})/({end}-{start})),1)"
            elif effect_type == 'emphasis_zoom':
                zoom_expr = f"if(between(t,{start},{end}),1+({1.6 * intensity}-1)*min(1,(t-{start})*2),1)"
            else:
                # Default zoom
                zoom_expr = f"if(between(t,{start},{end}),{1.4 * intensity},1)"
            
            zoom_expressions.append(zoom_expr)
        
        # Combine zoom expressions
        if len(zoom_expressions) == 1:
            final_zoom = zoom_expressions[0]
        else:
            final_zoom = '*'.join(f"({expr})" for expr in zoom_expressions)
        
        # Apply zoom filter
        output_path = self.temp_dir / f"zoomed_{int(time.time())}.mp4"
        zoom_filter = f"zoompan=z='{final_zoom}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', zoom_filter,
            '-c:a', 'copy',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        
        if result.returncode != 0:
            raise Exception(f"Zoom effects failed: {result.stderr}")
        
        return str(output_path)
    
    async def _apply_caption_effects(self, video_path: str, plan_file: str) -> str:
        """Apply AI-determined caption effects"""
        # Load effect plan
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        caption_effects = plan.get('caption_effects', [])
        
        if not caption_effects:
            # No caption effects, return input
            return video_path
        
        # Create caption filters
        caption_filters = []
        for i, effect in enumerate(caption_effects):
            start = effect['start_time']
            end = effect['end_time']
            text = effect['parameters'].get('text_content', 'Key Point')
            position = effect['parameters'].get('position', 'center')
            
            # Position mapping
            pos_map = {
                'center': 'x=(w-text_w)/2:y=(h-text_h)/2',
                'top': 'x=(w-text_w)/2:y=50',
                'bottom': 'x=(w-text_w)/2:y=h-text_h-50',
                'left': 'x=50:y=(h-text_h)/2',
                'right': 'x=w-text_w-50:y=(h-text_h)/2'
            }
            
            pos_str = pos_map.get(position, pos_map['center'])
            
            caption_filter = f"drawtext=text='{text}':fontsize=48:fontcolor=white:bordercolor=black:borderw=2:{pos_str}:enable='between(t,{start},{end})'"
            caption_filters.append(caption_filter)
        
        if caption_filters:
            # Apply caption filters
            output_path = self.temp_dir / f"captioned_{int(time.time())}.mp4"
            filter_str = ','.join(caption_filters)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf', filter_str,
                '-c:a', 'copy',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0:
                raise Exception(f"Caption effects failed: {result.stderr}")
            
            return str(output_path)
        
        return video_path
    
    async def _apply_overlay_effects(self, video_path: str, plan_file: str) -> str:
        """Apply AI-determined overlay effects"""
        # For now, return input (overlay effects can be complex)
        # This is where you'd add arrows, circles, highlights, etc.
        return video_path
    
    async def _apply_logo_overlay(self, video_path: str, logo_path: Path) -> str:
        """Apply logo overlay"""
        output_path = self.temp_dir / f"logo_overlay_{int(time.time())}.mp4"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', str(logo_path),
            '-filter_complex', '[1:v]scale=100:100[logo];[0:v][logo]overlay=W-w-20:20',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        
        if result.returncode != 0:
            raise Exception(f"Logo overlay failed: {result.stderr}")
        
        return str(output_path)
    
    async def _final_assembly(self, video_path: str, job_id: str) -> str:
        """Final assembly and optimization"""
        output_path = self.temp_dir / f"final_{job_id}.mp4"
        
        # Optimize final video
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        
        if result.returncode != 0:
            raise Exception(f"Final assembly failed: {result.stderr}")
        
        return str(output_path)
    
    async def _cleanup_temp_files(self, job_id: str) -> str:
        """Cleanup temporary files (keep final output)"""
        job_temp_dir = self.temp_dir / job_id
        
        # Clean up intermediate files but keep final output
        for file_path in job_temp_dir.glob("*"):
            if not file_path.name.startswith("final_"):
                try:
                    file_path.unlink()
                except:
                    pass
        
        return "cleanup_completed"
