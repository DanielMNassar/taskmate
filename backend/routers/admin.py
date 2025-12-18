"""
Admin-only endpoints for seeding and maintenance.
NOT exposed in UI - accessed via direct URL with token authentication.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.db import get_db
from backend import models
from backend.auth import hash_password

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()


def verify_admin_token(token: Optional[str] = Query(None)) -> bool:
    """Verify admin token from query parameter against env var."""
    expected_token = os.getenv("ADMIN_SEED_TOKEN", "super-secret-demo-token")
    
    if not token or token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid or missing admin token")
    
    return True


@router.post("/seed")
def seed_database(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_token)
):
    """
    Seed the database with demo data for Lebanon marketplace.
    
    Access: POST /admin/seed?token=YOUR_ADMIN_TOKEN
    
    Seeds:
    - Service areas (Lebanon regions)
    - Service categories
    - Demo customers (2)
    - Demo providers (3)
    
    All passwords are hashed using bcrypt_sha256.
    Demo credentials are printed to server logs only.
    """
    
    try:
        # ========================================
        # 1. SERVICE AREAS (Lebanon)
        # ========================================
        areas_data = [
            {"city": "Beirut", "district": "Achrafieh", "postal_code": "1100"},
            {"city": "Beirut", "district": "Hamra", "postal_code": "1103"},
            {"city": "Beirut", "district": "Verdun", "postal_code": "1102"},
            {"city": "Mount Lebanon", "district": "Jounieh", "postal_code": "1200"},
            {"city": "Mount Lebanon", "district": "Jbeil", "postal_code": "1201"},
            {"city": "Mount Lebanon", "district": "Baabda", "postal_code": "1202"},
            {"city": "North Lebanon", "district": "Tripoli", "postal_code": "1300"},
            {"city": "North Lebanon", "district": "Zgharta", "postal_code": "1301"},
            {"city": "South Lebanon", "district": "Sidon", "postal_code": "1400"},
            {"city": "South Lebanon", "district": "Tyre", "postal_code": "1401"},
            {"city": "Bekaa", "district": "Zahle", "postal_code": "1500"},
            {"city": "Bekaa", "district": "Baalbek", "postal_code": "1501"},
        ]
        
        areas = []
        for area_data in areas_data:
            # Check if area already exists
            existing = db.query(models.ServiceArea).filter_by(
                city=area_data["city"],
                district=area_data["district"]
            ).first()
            
            if not existing:
                area = models.ServiceArea(**area_data)
                db.add(area)
                areas.append(area)
            else:
                areas.append(existing)
        
        db.commit()
        logger.info(f"✓ Seeded {len(areas_data)} service areas")
        
        # ========================================
        # 2. SERVICE CATEGORIES
        # ========================================
        categories_data = [
            {"name": "Electrician", "description": "Electrical repairs and installations"},
            {"name": "Plumber", "description": "Plumbing repairs and installations"},
            {"name": "Mechanic", "description": "Car and vehicle repairs"},
            {"name": "Cleaning", "description": "Home and office cleaning services"},
            {"name": "AC Repair", "description": "Air conditioning repair and maintenance"},
            {"name": "Carpenter", "description": "Carpentry and furniture work"},
            {"name": "Painter", "description": "Interior and exterior painting"},
        ]
        
        categories = []
        for cat_data in categories_data:
            existing = db.query(models.ServiceCategory).filter_by(name=cat_data["name"]).first()
            
            if not existing:
                category = models.ServiceCategory(**cat_data)
                db.add(category)
                categories.append(category)
            else:
                categories.append(existing)
        
        db.commit()
        logger.info(f"✓ Seeded {len(categories_data)} service categories")
        
        # ========================================
        # 3. DEMO CUSTOMERS
        # ========================================
        customers_data = [
            {
                "first_name": "Ali",
                "last_name": "Hassan",
                "email": "ali@customer.com",
                "phone": "+961 70 123456",
                "address": "Mar Elias Street, Beirut",
                "area": areas[0],  # Beirut - Achrafieh
                "password": "customer123"
            },
            {
                "first_name": "Sara",
                "last_name": "Khalil",
                "email": "sara@customer.com",
                "phone": "+961 76 654321",
                "address": "Hamra Main Street, Beirut",
                "area": areas[1],  # Beirut - Hamra
                "password": "customer123"
            },
        ]
        
        demo_customers_log = []
        for cust_data in customers_data:
            existing = db.query(models.Customer).filter_by(email=cust_data["email"]).first()
            
            if not existing:
                plain_password = cust_data.pop("password")
                area = cust_data.pop("area")
                
                customer = models.Customer(
                    **cust_data,
                    area_id=area.area_id,
                    password_hash=hash_password(plain_password)
                )
                db.add(customer)
                demo_customers_log.append({
                    "name": f"{cust_data['first_name']} {cust_data['last_name']}",
                    "email": cust_data["email"],
                    "password": plain_password,
                    "role": "customer"
                })
        
        db.commit()
        logger.info(f"✓ Seeded {len(customers_data)} demo customers")
        
        # ========================================
        # 4. DEMO PROVIDERS
        # ========================================
        providers_data = [
            {
                "first_name": "Hassan",
                "last_name": "Electrician",
                "email": "hassan@provider.com",
                "phone": "+961 70 111222",
                "address": "Downtown Beirut",
                "area": areas[0],  # Beirut - Achrafieh
                "hourly_rate": 35.00,
                "password": "provider123",
                "categories": [categories[0]],  # Electrician
            },
            {
                "first_name": "Rami",
                "last_name": "Plumber",
                "email": "rami@provider.com",
                "phone": "+961 70 999888",
                "address": "Jounieh Center",
                "area": areas[3],  # Mount Lebanon - Jounieh
                "hourly_rate": 30.00,
                "password": "provider123",
                "categories": [categories[1]],  # Plumber
            },
            {
                "first_name": "Nabil",
                "last_name": "Mechanic",
                "email": "nabil@provider.com",
                "phone": "+961 71 555444",
                "address": "Tripoli Industrial Zone",
                "area": areas[6],  # North Lebanon - Tripoli
                "hourly_rate": 40.00,
                "password": "provider123",
                "categories": [categories[2]],  # Mechanic
            },
            {
                "first_name": "Layla",
                "last_name": "Cleaning",
                "email": "layla@provider.com",
                "phone": "+961 76 333222",
                "address": "Verdun Street, Beirut",
                "area": areas[2],  # Beirut - Verdun
                "hourly_rate": 25.00,
                "password": "provider123",
                "categories": [categories[3]],  # Cleaning
            },
        ]
        
        demo_providers_log = []
        for prov_data in providers_data:
            existing = db.query(models.ServiceProvider).filter_by(email=prov_data["email"]).first()
            
            if not existing:
                plain_password = prov_data.pop("password")
                area = prov_data.pop("area")
                provider_categories = prov_data.pop("categories")
                
                provider = models.ServiceProvider(
                    **prov_data,
                    area_id=area.area_id,
                    availability_status=models.AvailabilityStatus.available,
                    password_hash=hash_password(plain_password)
                )
                db.add(provider)
                db.flush()  # Get provider_id
                
                # Add provider categories
                for category in provider_categories:
                    prov_cat = models.ProviderCategory(
                        provider_id=provider.provider_id,
                        category_id=category.category_id
                    )
                    db.add(prov_cat)
                
                demo_providers_log.append({
                    "name": f"{prov_data['first_name']} {prov_data['last_name']}",
                    "email": prov_data["email"],
                    "password": plain_password,
                    "role": "provider"
                })
        
        db.commit()
        logger.info(f"✓ Seeded {len(providers_data)} demo providers")
        
        # ========================================
        # LOG DEMO CREDENTIALS (SERVER LOGS ONLY)
        # ========================================
        logger.info("=" * 60)
        logger.info("DEMO CREDENTIALS (for testing only)")
        logger.info("=" * 60)
        
        logger.info("\n📧 CUSTOMERS:")
        for cust in demo_customers_log:
            logger.info(f"  • {cust['name']}")
            logger.info(f"    Email: {cust['email']}")
            logger.info(f"    Password: {cust['password']}")
            logger.info("")
        
        logger.info("🔧 PROVIDERS:")
        for prov in demo_providers_log:
            logger.info(f"  • {prov['name']}")
            logger.info(f"    Email: {prov['email']}")
            logger.info(f"    Password: {prov['password']}")
            logger.info("")
        
        logger.info("=" * 60)
        logger.info("✓ Database seeded successfully!")
        logger.info("=" * 60)
        
        # Return success response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Database seeded successfully",
                "seeded": {
                    "areas": len(areas_data),
                    "categories": len(categories_data),
                    "customers": len(demo_customers_log),
                    "providers": len(demo_providers_log),
                },
                "note": "Demo credentials printed to server logs"
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seeding failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")


@router.get("/seed")
def seed_get_redirect():
    """Redirect GET requests to use POST."""
    return JSONResponse(
        status_code=405,
        content={
            "error": "Method not allowed",
            "message": "Please use POST /admin/seed?token=YOUR_TOKEN"
        }
    )
