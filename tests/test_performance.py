"""
Performance and load tests for video processing API
"""
import pytest
import time
import asyncio
import concurrent.futures
from typing import List, Dict, Any
import statistics

class TestPerformance:
    """Performance tests for video processing"""
    
    @pytest.mark.performance
    def test_credit_calculation_performance(self, credit_manager):
        """Test credit calculation performance"""
        # Test with various job configurations
        test_cases = [
            {
                "job_type": "simple_merge",
                "videos": [{"duration": 30.0}, {"duration": 45.0}],
                "options": {"platform": "youtube", "quality_preset": "balanced"}
            },
            {
                "job_type": "auto_effects",
                "videos": [{"duration": 120.0}],
                "options": {
                    "platform": "tiktok",
                    "quality_preset": "quality",
                    "auto_effects": True,
                    "enable_transcription": True
                }
            },
            {
                "job_type": "multi_video",
                "videos": [{"duration": 20.0}, {"duration": 30.0}, {"duration": 25.0}, {"duration": 40.0}],
                "options": {"platform": "youtube", "quality_preset": "balanced"}
            }
        ]
        
        times = []
        
        for test_case in test_cases:
            start_time = time.time()
            
            # Run calculation multiple times
            for _ in range(100):
                result = credit_manager.calculate_credits_for_job(
                    test_case["job_type"],
                    test_case["videos"],
                    test_case["options"]
                )
                assert result["total_credits"] >= 0
            
            end_time = time.time()
            avg_time = (end_time - start_time) / 100
            times.append(avg_time)
            
            print(f"Credit calculation for {test_case['job_type']}: {avg_time*1000:.2f}ms avg")
        
        # Overall performance should be fast
        overall_avg = statistics.mean(times)
        assert overall_avg < 0.01, f"Credit calculation too slow: {overall_avg*1000:.2f}ms"
        
        print(f"Overall credit calculation performance: {overall_avg*1000:.2f}ms avg")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_api_response_times(self, test_client, auth_headers):
        """Test API endpoint response times"""
        endpoints = [
            ("GET", "/", {}),
            ("GET", "/health", {}),
            ("GET", "/credits", {}),
            ("GET", "/jobs", {}),
            ("POST", "/credits/estimate", {
                "job_type": "simple_merge",
                "videos": [
                    {"url": "https://example.com/video.mp4", "duration": 30.0, "order_index": 0}
                ],
                "processing_options": {"platform": "youtube"}
            })
        ]
        
        response_times = {}
        
        for method, endpoint, data in endpoints:
            times = []
            
            for _ in range(10):  # Test each endpoint 10 times
                start_time = time.time()
                
                if method == "GET":
                    response = test_client.get(endpoint, headers=auth_headers)
                elif method == "POST":
                    response = test_client.post(endpoint, json=data, headers=auth_headers)
                
                end_time = time.time()
                response_time = end_time - start_time
                times.append(response_time)
                
                # Basic assertion that request succeeded or failed gracefully
                assert response.status_code < 500, f"Server error on {method} {endpoint}"
            
            avg_time = statistics.mean(times)
            response_times[f"{method} {endpoint}"] = avg_time
            
            print(f"{method} {endpoint}: {avg_time*1000:.2f}ms avg")
        
        # API responses should be fast
        for endpoint, avg_time in response_times.items():
            assert avg_time < 2.0, f"API response too slow for {endpoint}: {avg_time*1000:.2f}ms"
    
    @pytest.mark.performance
    def test_concurrent_credit_operations(self, credit_manager, test_user):
        """Test concurrent credit operations"""
        from uuid import UUID, uuid4
        
        user_id = UUID(test_user["user_id"])
        
        def perform_credit_operations():
            """Perform a series of credit operations"""
            job_id = uuid4()
            
            # Reserve credits
            success = credit_manager.reserve_credits(user_id, 10, job_id)
            if success:
                # Finalize credits
                credit_manager.finalize_credits(user_id, 10, 8, job_id)
            
            return success
        
        # Run concurrent operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(perform_credit_operations) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # Check that most operations succeeded (some might fail due to insufficient credits)
        success_rate = sum(results) / len(results)
        print(f"Concurrent credit operations success rate: {success_rate:.2%}")
        print(f"Total time for 20 concurrent operations: {end_time - start_time:.2f}s")
        
        # Should complete reasonably quickly
        assert end_time - start_time < 10.0, "Concurrent operations took too long"


class TestLoadTesting:
    """Load testing for the API"""
    
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_concurrent_job_creation(self, api_helper, sample_videos, storage_service, test_credits):
        """Test creating multiple jobs concurrently"""
        # Upload a test video
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/load_test_video.mp4"
        )
        
        if not video_url:
            pytest.skip("Could not upload test video")
        
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": video_url, "order_index": 0},
                {"url": video_url, "order_index": 1}
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "fast"
            }
        }
        
        async def create_job():
            """Create a single job"""
            try:
                job_response, status_code = api_helper.create_job(job_data)
                return status_code == 200
            except Exception as e:
                print(f"Job creation failed: {e}")
                return False
        
        # Create multiple jobs concurrently
        start_time = time.time()
        
        tasks = [create_job() for _ in range(5)]  # Create 5 jobs concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Count successful job creations
        successful_jobs = sum(1 for result in results if result is True)
        
        print(f"Created {successful_jobs}/5 jobs successfully in {end_time - start_time:.2f}s")
        
        # At least some jobs should succeed
        assert successful_jobs > 0, "No jobs were created successfully"
    
    @pytest.mark.load
    def test_database_connection_pool(self, db_service):
        """Test database connection handling under load"""
        def perform_db_operation():
            """Perform a database operation"""
            try:
                # Test a simple database operation
                result = db_service.count_total_jobs()
                return isinstance(result, int)
            except Exception as e:
                print(f"DB operation failed: {e}")
                return False
        
        # Perform many concurrent database operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(perform_db_operation) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        success_rate = sum(results) / len(results)
        
        print(f"Database operations success rate: {success_rate:.2%}")
        print(f"Time for 50 concurrent DB operations: {end_time - start_time:.2f}s")
        
        # Most operations should succeed
        assert success_rate > 0.8, f"Too many database operations failed: {success_rate:.2%}"
    
    @pytest.mark.load
    def test_memory_usage_during_processing(self, video_processor, sample_videos, temp_output_dir):
        """Test memory usage during video processing"""
        import psutil
        import os
        
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip("Test video not found")
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple video operations
        for i in range(3):
            output_path = temp_output_dir / f"memory_test_{i}.mp4"
            
            # Simple merge operation
            result = video_processor.simple_merge([main_video, main_video], output_path)
            
            if result["success"]:
                # Check memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                print(f"Memory usage after operation {i+1}: {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
                
                # Memory usage shouldn't grow excessively
                assert memory_increase < 500, f"Memory usage increased too much: {memory_increase:.1f}MB"
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        print(f"Total memory increase: {total_increase:.1f}MB")
        
        # Should not have significant memory leaks
        assert total_increase < 200, f"Possible memory leak detected: {total_increase:.1f}MB increase"


class TestScalability:
    """Test system scalability"""
    
    @pytest.mark.scalability
    def test_large_video_handling(self, video_processor, temp_output_dir):
        """Test handling of large video files (simulated)"""
        # This test simulates large video processing without actually using large files
        
        # Simulate video info for a large file
        large_video_info = {
            "duration": 3600.0,  # 1 hour
            "size": 2 * 1024 * 1024 * 1024,  # 2GB
            "width": 1920,
            "height": 1080
        }
        
        # Test credit calculation for large video
        from services.credit_manager import CreditManager
        credit_manager = CreditManager()
        
        videos = [{"duration": large_video_info["duration"]}]
        options = {
            "platform": "youtube",
            "quality_preset": "quality",
            "auto_effects": True,
            "enable_transcription": True
        }
        
        result = credit_manager.calculate_credits_for_job(
            "auto_effects",
            videos,
            options
        )
        
        # Should handle large videos gracefully
        assert result["total_credits"] > 0
        assert result["total_duration_seconds"] == large_video_info["duration"]
        
        print(f"Credits for 1-hour video with auto effects: {result['total_credits']}")
    
    @pytest.mark.scalability
    def test_many_small_videos(self, credit_manager):
        """Test handling many small videos"""
        # Simulate processing many small videos
        videos = [{"duration": 5.0} for _ in range(20)]  # 20 videos of 5 seconds each
        
        options = {
            "platform": "youtube",
            "quality_preset": "balanced"
        }
        
        start_time = time.time()
        
        result = credit_manager.calculate_credits_for_job(
            "multi_video",
            videos,
            options
        )
        
        end_time = time.time()
        
        # Should handle many videos efficiently
        assert result["total_credits"] > 0
        assert end_time - start_time < 1.0, "Processing many videos took too long"
        
        print(f"Credits for 20 small videos: {result['total_credits']}")
        print(f"Calculation time: {(end_time - start_time)*1000:.2f}ms")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__, 
        "-v", 
        "-m", "performance",
        "--tb=short"
    ])
