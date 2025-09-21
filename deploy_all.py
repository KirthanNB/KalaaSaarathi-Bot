#!/usr/bin/env python3
import os
import subprocess
from deploy_shop import create_shop_index, deploy_to_firebase, get_all_products

def deploy_all():
    """Deploy everything to Firebase"""
    print("🚀 Starting complete deployment...")
    
    # 0. Initialize JSON files first
    print("📝 Initializing JSON files...")
    from deploy_shop import initialize_json_files
    initialize_json_files()
    
    # 1. Create shop index
    print("📋 Creating shop index...")
    create_shop_index()
    
    # 2. Verify what files are created
    print("🔍 Verifying created files...")
    from deploy_shop import verify_deployment_files
    verify_deployment_files()
    
    # 3. Deploy to Firebase
    print("☁️  Deploying to Firebase...")
    success = deploy_to_firebase()
    
    if success:
        print("✅ Deployment completed successfully!")
        print("🌐 Your shop is live at: https://neethi-saarathi-ids.web.app")
        
        # Test if products are accessible
        test_products_access()
    else:
        print("❌ Deployment failed!")
    
    return success

def test_products_access():
    """Test if products are accessible"""
    print("🧪 Testing product access...")
    
    products = get_all_products()
    if products:
        print(f"✅ Found {len(products)} products in products.json")
        
        # Test a few product URLs
        for product in products[-3:]:  # Test last 3 products
            product_id = product.get('id')
            product_url = f"https://neethi-saarathi-ids.web.app/product/{product_id}.html"
            print(f"   Testing: {product_url}")
            
            # You could add actual HTTP testing here if needed
    else:
        print("❌ No products found in products.json!")

if __name__ == "__main__":
    deploy_all()