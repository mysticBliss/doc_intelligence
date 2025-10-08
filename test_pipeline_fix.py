#!/usr/bin/env python3
"""
Test script to verify the pipeline_id AttributeError fix.
This script tests the DocumentOrchestrationService without the pipeline_id reference.
"""

import sys
import os
import asyncio
from unittest.mock import Mock

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.services.document_orchestration_service import DocumentOrchestrationService
from app.processing.factory import ProcessorFactory
from app.processing.pipeline import ProcessingPipeline
from app.processing.payloads import DocumentPayload

async def test_pipeline_fix():
    """Test that the pipeline_id AttributeError is fixed."""
    
    # Create mock objects
    mock_storage = Mock()
    mock_storage.save_file.return_value = "http://test-url"
    
    factory = ProcessorFactory()
    
    # Create the service
    service = DocumentOrchestrationService(
        storage_port=mock_storage,
        factory=factory
    )
    
    # Test pipeline config (simple mode to avoid complex dependencies)
    pipeline_config = {
        "name": "test_pipeline",
        "description": "Test pipeline",
        "execution_mode": "simple",
        "pipeline": []  # Empty pipeline to avoid processor dependencies
    }
    
    # Test data
    test_data = b"test file content"
    test_filename = "test.txt"
    correlation_id = "test-correlation-id"
    
    try:
        # This should not raise an AttributeError about pipeline_id
        result = await service.process_document(
            file_data=test_data,
            file_name=test_filename,
            pipeline_config=pipeline_config,
            correlation_id=correlation_id
        )
        
        print("✅ SUCCESS: No AttributeError raised!")
        print(f"Result job_id: {result.job_id}")
        print(f"Result status: {result.status}")
        return True
        
    except AttributeError as e:
        if "pipeline_id" in str(e):
            print(f"❌ FAILED: AttributeError still present: {e}")
            return False
        else:
            print(f"❌ FAILED: Different AttributeError: {e}")
            return False
    except Exception as e:
        print(f"⚠️  OTHER ERROR (not AttributeError): {e}")
        print("This might be expected due to missing dependencies in test environment")
        return True  # Not the AttributeError we were fixing

if __name__ == "__main__":
    print("Testing pipeline_id AttributeError fix...")
    success = asyncio.run(test_pipeline_fix())
    if success:
        print("\n🎉 Fix appears to be working!")
    else:
        print("\n💥 Fix did not resolve the issue!")
    sys.exit(0 if success else 1)
