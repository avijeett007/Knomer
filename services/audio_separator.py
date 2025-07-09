"""
Audio separation service for extracting voice and music from videos
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import tempfile
import json
import time

logger = logging.getLogger(__name__)

class AudioSeparator:
    """Service for separating audio into voice and music components"""
    
    def __init__(self):
        self.temp_dir = Path("/tmp/audio_separation")
        self.temp_dir.mkdir(exist_ok=True)
    
    def separate_audio_from_video(
        self, 
        video_path: Path, 
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Extract and separate audio from video into voice and music components
        
        Args:
            video_path: Path to input video file
            output_dir: Optional output directory (defaults to temp dir)
            
        Returns:
            Dictionary with paths to separated audio files and metadata
        """
        try:
            if output_dir is None:
                output_dir = self.temp_dir / f"separation_{int(time.time())}"

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Extract audio from video
            logger.info(f"Extracting audio from video: {video_path}")
            audio_path = self._extract_audio_from_video(video_path, output_dir)
            
            # Step 2: Get audio metadata
            audio_metadata = self._get_audio_metadata(audio_path)
            
            # Step 3: Separate voice and music using FFmpeg filters
            logger.info("Separating voice and music components")
            voice_path, music_path = self._separate_voice_and_music(audio_path, output_dir)
            
            # Step 4: Enhance separated tracks
            enhanced_voice_path = self._enhance_voice_track(voice_path, output_dir)
            enhanced_music_path = self._enhance_music_track(music_path, output_dir)
            
            # Step 5: Create analysis report
            analysis = self._analyze_separation_quality(
                audio_path, enhanced_voice_path, enhanced_music_path
            )
            
            result = {
                "success": True,
                "original_audio": str(audio_path),
                "separated_voice": str(enhanced_voice_path),
                "separated_music": str(enhanced_music_path),
                "raw_voice": str(voice_path),
                "raw_music": str(music_path),
                "metadata": audio_metadata,
                "analysis": analysis,
                "output_directory": str(output_dir)
            }
            
            logger.info("Audio separation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Audio separation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_audio": None,
                "separated_voice": None,
                "separated_music": None
            }
    
    def _extract_audio_from_video(self, video_path: Path, output_dir: Path) -> Path:
        """Extract audio track from video file"""
        audio_path = output_dir / "extracted_audio.wav"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Uncompressed audio for better processing
            '-ar', '44100',  # Standard sample rate
            '-ac', '2',  # Stereo
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise Exception(f"Audio extraction failed: {result.stderr}")
        
        return audio_path
    
    def _get_audio_metadata(self, audio_path: Path) -> Dict[str, Any]:
        """Get detailed metadata about the audio file"""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams',
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Could not get audio metadata: {result.stderr}")
            return {}
        
        try:
            metadata = json.loads(result.stdout)
            audio_stream = next(
                (stream for stream in metadata.get('streams', []) 
                 if stream.get('codec_type') == 'audio'), 
                {}
            )
            
            return {
                "duration": float(metadata.get('format', {}).get('duration', 0)),
                "sample_rate": int(audio_stream.get('sample_rate', 0)),
                "channels": int(audio_stream.get('channels', 0)),
                "bit_rate": int(audio_stream.get('bit_rate', 0)),
                "codec": audio_stream.get('codec_name', 'unknown'),
                "size_bytes": int(metadata.get('format', {}).get('size', 0))
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Could not parse audio metadata: {e}")
            return {}
    
    def _separate_voice_and_music(self, audio_path: Path, output_dir: Path) -> Tuple[Path, Path]:
        """
        Separate voice and music using FFmpeg audio filters
        This uses spectral analysis and frequency filtering techniques
        """
        voice_path = output_dir / "voice_raw.wav"
        music_path = output_dir / "music_raw.wav"
        
        # Voice extraction filter (focuses on vocal frequency range)
        voice_filter = (
            "highpass=f=80,"  # Remove low-frequency rumble
            "lowpass=f=8000,"  # Remove very high frequencies
            "bandpass=f=1000:width_type=h:width=2000,"  # Focus on vocal range
            "compand=attacks=0.3:decays=0.8:points=-70/-70|-60/-20|-20/-10|-10/-5|0/-3"  # Dynamic range compression
        )
        
        # Music extraction filter (removes vocal frequencies)
        music_filter = (
            "highpass=f=20,"  # Keep low frequencies
            "bandreject=f=1000:width_type=h:width=1500,"  # Remove vocal range
            "compand=attacks=0.1:decays=0.3:points=-80/-80|-50/-30|-30/-15|-15/-10|0/-5"  # Preserve dynamics
        )
        
        # Extract voice
        voice_cmd = [
            'ffmpeg', '-y',
            '-i', str(audio_path),
            '-af', voice_filter,
            '-acodec', 'pcm_s16le',
            str(voice_path)
        ]
        
        # Extract music
        music_cmd = [
            'ffmpeg', '-y',
            '-i', str(audio_path),
            '-af', music_filter,
            '-acodec', 'pcm_s16le',
            str(music_path)
        ]
        
        # Run voice extraction
        result = subprocess.run(voice_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise Exception(f"Voice extraction failed: {result.stderr}")
        
        # Run music extraction
        result = subprocess.run(music_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise Exception(f"Music extraction failed: {result.stderr}")
        
        return voice_path, music_path
    
    def _enhance_voice_track(self, voice_path: Path, output_dir: Path) -> Path:
        """Enhance the separated voice track for clarity"""
        enhanced_voice_path = output_dir / "voice_enhanced.wav"
        
        # Voice enhancement filter
        enhancement_filter = (
            "equalizer=f=2000:width_type=h:width=500:g=3,"  # Boost presence
            "equalizer=f=4000:width_type=h:width=1000:g=2,"  # Boost clarity
            "compand=attacks=0.02:decays=0.2:points=-60/-60|-30/-20|-20/-10|-10/-5|0/-3,"  # Compression
            "highpass=f=100,"  # Remove low-frequency noise
            "lowpass=f=7000,"  # Remove high-frequency noise
            "volume=1.5"  # Slight volume boost
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(voice_path),
            '-af', enhancement_filter,
            '-acodec', 'pcm_s16le',
            str(enhanced_voice_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.warning(f"Voice enhancement failed, using raw voice: {result.stderr}")
            return voice_path
        
        return enhanced_voice_path
    
    def _enhance_music_track(self, music_path: Path, output_dir: Path) -> Path:
        """Enhance the separated music track"""
        enhanced_music_path = output_dir / "music_enhanced.wav"
        
        # Music enhancement filter
        enhancement_filter = (
            "equalizer=f=60:width_type=h:width=40:g=2,"  # Boost bass
            "equalizer=f=10000:width_type=h:width=5000:g=1,"  # Slight treble boost
            "compand=attacks=0.1:decays=0.5:points=-70/-70|-40/-30|-20/-15|-10/-8|0/-5,"  # Gentle compression
            "volume=0.8"  # Slight volume reduction to balance with voice
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(music_path),
            '-af', enhancement_filter,
            '-acodec', 'pcm_s16le',
            str(enhanced_music_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.warning(f"Music enhancement failed, using raw music: {result.stderr}")
            return music_path
        
        return enhanced_music_path
    
    def _analyze_separation_quality(
        self, 
        original_path: Path, 
        voice_path: Path, 
        music_path: Path
    ) -> Dict[str, Any]:
        """Analyze the quality of the audio separation"""
        try:
            # Get RMS levels for quality assessment
            original_rms = self._get_audio_rms(original_path)
            voice_rms = self._get_audio_rms(voice_path)
            music_rms = self._get_audio_rms(music_path)
            
            # Calculate separation metrics
            voice_ratio = voice_rms / original_rms if original_rms > 0 else 0
            music_ratio = music_rms / original_rms if original_rms > 0 else 0
            
            # Quality assessment
            quality_score = min(1.0, (voice_ratio + music_ratio) * 0.7)  # Rough quality metric
            
            return {
                "original_rms": original_rms,
                "voice_rms": voice_rms,
                "music_rms": music_rms,
                "voice_ratio": voice_ratio,
                "music_ratio": music_ratio,
                "quality_score": quality_score,
                "quality_rating": self._get_quality_rating(quality_score)
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze separation quality: {e}")
            return {
                "quality_score": 0.5,
                "quality_rating": "unknown",
                "error": str(e)
            }
    
    def _get_audio_rms(self, audio_path: Path) -> float:
        """Get RMS (Root Mean Square) level of audio file"""
        cmd = [
            'ffmpeg', '-i', str(audio_path),
            '-af', 'volumedetect',
            '-vn', '-sn', '-dn',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Parse RMS from output
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                try:
                    rms_db = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    return 10 ** (rms_db / 20)  # Convert dB to linear
                except (ValueError, IndexError):
                    pass
        
        return 0.0
    
    def _get_quality_rating(self, score: float) -> str:
        """Convert quality score to human-readable rating"""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        elif score >= 0.2:
            return "poor"
        else:
            return "very_poor"
    
    def create_mixed_output(
        self, 
        voice_path: Path, 
        music_path: Path, 
        output_path: Path,
        voice_volume: float = 1.0,
        music_volume: float = 0.7
    ) -> Path:
        """
        Create a new mixed audio file from separated voice and music
        
        Args:
            voice_path: Path to voice track
            music_path: Path to music track
            output_path: Path for output mixed file
            voice_volume: Volume multiplier for voice (default 1.0)
            music_volume: Volume multiplier for music (default 0.7)
        """
        cmd = [
            'ffmpeg', '-y',
            '-i', str(voice_path),
            '-i', str(music_path),
            '-filter_complex', 
            f'[0:a]volume={voice_volume}[voice];[1:a]volume={music_volume}[music];[voice][music]amix=inputs=2:duration=longest',
            '-acodec', 'pcm_s16le',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"Audio mixing failed: {result.stderr}")
        
        return output_path

    def _convert_audio_format(self, input_path: Path, output_path: Path, format: str) -> Path:
        """Convert audio file to specified format"""
        format_configs = {
            'mp3': ['-acodec', 'libmp3lame', '-b:a', '192k'],
            'flac': ['-acodec', 'flac'],
            'aac': ['-acodec', 'aac', '-b:a', '128k'],
            'wav': ['-acodec', 'pcm_s16le']
        }

        codec_args = format_configs.get(format, format_configs['wav'])

        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path)
        ] + codec_args + [str(output_path)]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise Exception(f"Audio format conversion failed: {result.stderr}")

        return output_path
