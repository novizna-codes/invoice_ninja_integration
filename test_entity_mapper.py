#!/usr/bin/env python3
"""
Simple test script to verify EntityMapper functionality
"""

import sys
import os

# Add the invoice_ninja_integration path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'invoice_ninja_integration'))

def test_entity_mapper():
    """Test EntityMapper validation functionality"""
    try:
        from utils.entity_mapper import EntityMapper
        
        print("=== Entity Mapper Test ===")
        print()
        
        # Test 1: Valid ERPNext doctypes (new standardized names)
        print("Testing VALID ERPNext doctypes:")
        valid_types = ['Customer', 'Sales Invoice', 'Quotation', 'Item', 'Payment Entry']
        for entity_type in valid_types:
            is_valid, result = EntityMapper.validate_entity_type(entity_type)
            status = "✓" if is_valid else "✗"
            print(f"  {entity_type:<20}: {status} {result if not is_valid else 'Valid'}")
        
        print()
        
        # Test 2: Invalid types (old naming convention that should fail)
        print("Testing INVALID entity types (old names):")
        invalid_types = ['Invoice', 'Quote', 'Product', 'Payment']
        for entity_type in invalid_types:
            is_valid, result = EntityMapper.validate_entity_type(entity_type)
            status = "✓" if is_valid else "✗"
            print(f"  {entity_type:<20}: {status}")
            if not is_valid:
                print(f"    Error: {result}")
        
        print()
        
        # Test 3: List all supported types
        print("All supported ERPNext doctypes:")
        for i, doctype in enumerate(EntityMapper.get_all_erpnext_doctypes(), 1):
            print(f"  {i}. {doctype}")
        
        print()
        
        # Test 4: Mapping functionality  
        print("Testing mapping functionality:")
        test_doctype = "Sales Invoice"
        config = EntityMapper.get_entity_config(test_doctype)
        if config:
            print(f"  {test_doctype}:")
            print(f"    Invoice Ninja endpoint: {config['invoice_ninja_endpoint']}")
            print(f"    Invoice Ninja entity: {config['invoice_ninja_entity']}")
            print(f"    Include params: {config['include_params']}")
        
        print()
        print("✅ EntityMapper test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    test_entity_mapper()