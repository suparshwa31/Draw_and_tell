#!/usr/bin/env python3
"""
Test script to measure CV service performance improvements
"""

import time
import os
from services.cv_service import cv_service

def test_cv_performance():
    """Test CV service performance with sample images"""
    
    # Find sample images in the data/images directory
    image_dir = "../data/images"
    if not os.path.exists(image_dir):
        print("❌ No sample images found. Please run the kid app first to generate some drawings.")
        return
    
    image_files = [f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print("❌ No image files found in data/images directory.")
        return
    
    print("🚀 Testing CV Service Performance Optimizations")
    print("=" * 60)
    
    total_time = 0
    successful_analyses = 0
    
    # Test with first few images
    test_images = image_files[:3]  # Test with first 3 images
    
    for i, image_file in enumerate(test_images):
        image_path = os.path.join(image_dir, image_file)
        
        print(f"\n📸 Testing image {i+1}: {image_file}")
        
        start_time = time.time()
        result = cv_service.analyze_drawing(image_path)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000
        total_time += duration
        
        if result["success"]:
            successful_analyses += 1
            print(f"   ✅ Success: {duration:.0f}ms")
            print(f"   📝 Caption: {result['caption']}")
            print(f"   ❓ Question: {result['question']}")
        else:
            print(f"   ❌ Failed: {duration:.0f}ms - {result.get('error', 'Unknown error')}")
    
    # Calculate statistics
    avg_time = total_time / len(test_images) if test_images else 0
    success_rate = (successful_analyses / len(test_images)) * 100 if test_images else 0
    
    print(f"\n📊 Performance Summary:")
    print(f"   Images tested: {len(test_images)}")
    print(f"   Successful analyses: {successful_analyses}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Average time: {avg_time:.0f}ms")
    print(f"   Total time: {total_time:.0f}ms")
    
    # Show cache info
    cache_info = cv_service.get_cache_info()
    print(f"\n🧠 Cache Statistics:")
    print(f"   Hits: {cache_info['hits']}")
    print(f"   Misses: {cache_info['misses']}")
    print(f"   Hit Rate: {cache_info['hits']/(cache_info['hits']+cache_info['misses']):.1%}" if (cache_info['hits']+cache_info['misses']) > 0 else "   Hit Rate: 0%")
    print(f"   Cache Size: {cache_info['current_size']}/{cache_info['max_size']}")
    
    # Performance recommendations
    print(f"\n💡 Performance Tips:")
    if avg_time > 2000:
        print("   ⚠️  Analysis is slow (>2s). Consider:")
        print("      - Using GPU if available")
        print("      - Reducing image size further")
        print("      - Using a smaller model")
    elif avg_time > 1000:
        print("   ⚡ Analysis is moderate (1-2s). Consider:")
        print("      - Enabling model compilation")
        print("      - Using mixed precision")
    else:
        print("   🚀 Analysis is fast (<1s). Great performance!")
    
    if cache_info['hits'] == 0 and len(test_images) > 1:
        print("   💾 No cache hits detected. Try running the same image twice to test caching.")

if __name__ == "__main__":
    test_cv_performance()
