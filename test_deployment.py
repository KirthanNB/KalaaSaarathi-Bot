#!/usr/bin/env python3
import requests
import json

def test_deployment():
    """Test if the deployment is working correctly"""
    base_url = "https://neethi-saarathi-ids.web.app"
    
    print("🧪 Testing deployment...")
    
    # Test 1: Main page
    print("1. Testing main page...")
    try:
        response = requests.get(base_url)
        print(f"   Status: {response.status_code}")
        print(f"   Content type: {response.headers.get('content-type')}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: Products JSON
    print("2. Testing products.json...")
    try:
        response = requests.get(f"{base_url}/products.json")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Products count: {len(data.get('products', []))}")
        else:
            print(f"   ❌ Failed with status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 3: Specific product HTML
    print("3. Testing product HTML file...")
    try:
        # Get a product ID from products.json
        response = requests.get(f"{base_url}/products.json")
        if response.status_code == 200:
            products = response.json().get('products', [])
            if products:
                product_id = products[0]['id']
                print(f"   Testing product: {product_id}")
                
                # Test with .html extension
                product_response = requests.get(f"{base_url}/product/{product_id}.html")
                print(f"   With .html: {product_response.status_code}")
                
                # Test without .html extension
                product_response2 = requests.get(f"{base_url}/product/{product_id}")
                print(f"   Without .html: {product_response2.status_code}")
            else:
                print("   ❌ No products found")
        else:
            print("   ❌ Could not fetch products.json")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    test_deployment()