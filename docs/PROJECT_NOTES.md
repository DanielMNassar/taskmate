# Project Notes

## Architecture Overview

This is a full-stack web application for managing home service requests, built with:
- **Backend:** FastAPI + SQLAlchemy + MySQL
- **Frontend:** Jinja2 templates + HTMX + Bootstrap 5
- **Database:** MySQL with full referential integrity

The application allows customers to:
- Search for service providers by area and category
- Create service requests
- Track request status
- Make payments for completed services
- Review providers

## Database Schema Summary

### Tables

1. **service_area** - Service coverage areas
   - `area_id` (PK, AUTO_INCREMENT)
   - `city`, `district`, `postal_code` (UNIQUE constraint on all three)

2. **service_category** - Types of services offered
   - `category_id` (PK, AUTO_INCREMENT)
   - `name` (UNIQUE)
   - `description`

3. **customer** - Service requesters
   - `customer_id` (PK, AUTO_INCREMENT)
   - `first_name`, `last_name`, `email` (UNIQUE), `phone`, `address`
   - `area_id` (FK → service_area, ON DELETE SET NULL)
   - `registration_date` (DEFAULT CURRENT_TIMESTAMP)

4. **service_provider** - Service providers
   - `provider_id` (PK, AUTO_INCREMENT)
   - `first_name`, `last_name`, `email` (UNIQUE), `phone`, `address`
   - `area_id` (FK → service_area, ON DELETE SET NULL)
   - `hourly_rate` (DECIMAL, CHECK >= 0)
   - `availability_status` (ENUM: available, busy, unavailable)
   - `date_joined` (DEFAULT CURRENT_TIMESTAMP)

5. **provider_category** - Many-to-many relationship
   - `provider_id` (PK, FK → service_provider, ON DELETE CASCADE)
   - `category_id` (PK, FK → service_category, ON DELETE CASCADE)

6. **service_request** - Service requests
   - `request_id` (PK, AUTO_INCREMENT)
   - `customer_id` (FK → customer, NOT NULL, ON DELETE CASCADE)
   - `provider_id` (FK → service_provider, ON DELETE SET NULL)
   - `category_id` (FK → service_category, NOT NULL, ON DELETE CASCADE)
   - `area_id` (FK → service_area, NOT NULL, ON DELETE CASCADE)
   - `address`, `description` (TEXT)
   - `status` (ENUM: pending, accepted, in_progress, completed, cancelled)
   - `cost` (DECIMAL, CHECK >= 0)
   - `request_date` (DEFAULT CURRENT_TIMESTAMP)
   - `cancellation_date` (nullable)

7. **payment** - Payments for service requests
   - `payment_id` (PK, AUTO_INCREMENT)
   - `request_id` (FK → service_request, UNIQUE, ON DELETE CASCADE)
   - `amount` (DECIMAL, NOT NULL, CHECK >= 0)
   - `payment_method` (ENUM: credit_card, debit_card, cash, paypal, bank_transfer)
   - `payment_status` (ENUM: pending, completed, failed, refunded)
   - `payment_date` (DEFAULT CURRENT_TIMESTAMP)

8. **review** - Reviews for completed services
   - `review_id` (PK, AUTO_INCREMENT)
   - `request_id` (FK → service_request, UNIQUE, ON DELETE CASCADE)
   - `customer_id` (FK → customer, NOT NULL, ON DELETE CASCADE)
   - `provider_id` (FK → service_provider, NOT NULL, ON DELETE CASCADE)
   - `rating` (INT, CHECK 1-5)
   - `comment` (TEXT)
   - `created_at` (DEFAULT CURRENT_TIMESTAMP)

### Key Constraints

- **Foreign Keys:** All FKs enforce referential integrity with appropriate CASCADE/SET NULL behavior
- **Unique Constraints:** Email addresses (customer, provider), request_id (payment, review)
- **Check Constraints:** Non-negative amounts/rates, rating 1-5
- **ENUM Types:** Status fields use MySQL ENUMs for data validation

## Migration Notes: Tkinter → FastAPI

### Original Application
- Built with Tkinter GUI and PostgreSQL
- Manual ID assignment for areas, providers, requests
- Direct SQL queries via psycopg2

### FastAPI Migration
- Converted to RESTful API with FastAPI
- Added web UI with Jinja2 + HTMX
- MySQL database (converted from PostgreSQL schema)
- AUTO_INCREMENT for all primary keys
- SQLAlchemy ORM instead of raw SQL

### Schema Changes
- `user_id` → `customer_id`
- `service_id` → `request_id`
- `category_name` → `name`
- Added `description` field to service_request
- Added `address` field to service_provider
- Added `area_id` to customer

### Function Mapping

| Old Tkinter Function | New FastAPI Endpoint | Status |
|---------------------|---------------------|--------|
| `add_customer()` | `POST /customers` | ✅ Complete |
| `load_customers()` | `GET /customers` | ✅ Complete |
| `add_area()` | `POST /areas` | ✅ Complete |
| `add_category()` | `POST /categories` | ✅ Complete |
| `add_provider()` | `POST /providers` | ✅ Complete |
| `add_request()` | `POST /service-requests` | ✅ Complete |
| `add_payment()` | `POST /payments` (with upsert) | ✅ Complete |

### Payment Upsert Logic
The old Tkinter app used MySQL's `ON DUPLICATE KEY UPDATE` for payments. The FastAPI version implements application-level upsert:
- Checks if payment exists for `request_id`
- Updates if exists, creates if not
- Preserves original `payment_date` on update

## Fixes Applied

### 1. Provider Query Logic (HIGH Priority)
**Issue:** `get_providers_by_area_category()` always joined ProviderCategory, excluding providers without categories when filtering by area only.

**Fix:** Made JOIN conditional - only joins when `category_id` filter is provided.

**File:** `backend/crud.py`

### 2. Review Validation (MEDIUM Priority)
**Issue:** Review creation didn't validate customer_id/provider_id match the service_request.

**Fix:** Added validation checks:
- Request must exist
- Customer ID must match
- Provider must be assigned (reject if NULL)
- Provider ID must match

**Files:** `backend/crud.py`, `backend/routers/reviews.py`

### 3. Duplicate Email Handling (HIGH Priority)
**Issue:** No friendly error messages for duplicate emails.

**Fix:** Added IntegrityError handling returning 409 Conflict with clear messages.

**Files:** `backend/crud.py`, `backend/routers/customers.py`, `backend/routers/providers.py`

### 4. Import Error Handling
**Issue:** Direct imports without fallback for package vs module execution.

**Fix:** Added try/except import patterns throughout.

**Files:** `backend/schemas.py`, `backend/models.py`, `backend/crud.py`, routers

## Manual Test Plan

### Prerequisites
1. Start FastAPI server: `uvicorn backend.main:app --reload`
2. Open Swagger UI: http://localhost:8000/docs
3. Ensure MySQL database is running and schema is applied

### Test Sequence

#### 1. Create Service Area
**Endpoint:** `POST /areas`
```json
{
  "city": "New York",
  "district": "Manhattan",
  "postal_code": "10001"
}
```
**Expected:** 201 Created with `area_id: 1`

#### 2. Create Service Category
**Endpoint:** `POST /categories`
```json
{
  "name": "Plumbing",
  "description": "Plumbing and pipe repair services"
}
```
**Expected:** 201 Created with `category_id: 1`

#### 3. Create Customer
**Endpoint:** `POST /customers`
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "555-0100",
  "address": "123 Main Street, Apt 4B",
  "area_id": 1
}
```
**Expected:** 201 Created with `customer_id: 1`

**Test Duplicate Email:**
- Try same payload again
- **Expected:** 409 Conflict

#### 4. Create Service Provider
**Endpoint:** `POST /providers`
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@example.com",
  "phone": "555-0200",
  "address": "456 Oak Avenue",
  "area_id": 1,
  "hourly_rate": 50.00,
  "availability_status": "available",
  "category_ids": [1]
}
```
**Expected:** 201 Created with `provider_id: 1`

#### 5. Test Provider Query - Area Only
**Endpoint:** `GET /providers?area_id=1`
**Expected:** Returns all providers in area 1 (including those without categories)

#### 6. Test Provider Query - Category Only
**Endpoint:** `GET /providers?category_id=1`
**Expected:** Returns only providers with category 1

#### 7. Create Service Request
**Endpoint:** `POST /service-requests`
```json
{
  "customer_id": 1,
  "provider_id": 1,
  "category_id": 1,
  "area_id": 1,
  "address": "789 Pine Street, Unit 5",
  "description": "Fix leaky kitchen faucet",
  "cost": 150.00
}
```
**Expected:** 201 Created with `request_id: 1`, `status: "pending"`

#### 8. Update Request Status
**Endpoint:** `PATCH /service-requests/1/status`
```json
{
  "status": "completed"
}
```
**Expected:** 200 OK with updated status

#### 9. Create Payment
**Endpoint:** `POST /payments`
```json
{
  "request_id": 1,
  "amount": 150.00,
  "payment_method": "credit_card",
  "payment_status": "completed"
}
```
**Expected:** 201 Created with `payment_id: 1`

**Test Payment Upsert:**
- Create payment again for same request_id
- **Expected:** Updates existing payment (upsert behavior)

#### 10. Create Review
**Endpoint:** `POST /reviews`
```json
{
  "request_id": 1,
  "customer_id": 1,
  "provider_id": 1,
  "rating": 5,
  "comment": "Excellent service!"
}
```
**Expected:** 201 Created with `review_id: 1`

**Test Review Validation:**
- Try with wrong customer_id
- **Expected:** 400 Bad Request

- Try with request that has no provider
- **Expected:** 400 Bad Request

- Try duplicate review
- **Expected:** 409 Conflict

## Demo Script (Presentation)

### Step 1: Setup (30 seconds)
1. Show project structure
2. Show database schema
3. Start server: `uvicorn backend.main:app --reload`

### Step 2: Web UI Demo (2 minutes)
1. Open http://localhost:8000/ui
2. Show provider search (select area/category, search)
3. Click "Request Service" on a provider
4. Fill form and submit
5. Show success message (HTMX update)

### Step 3: My Requests Page (1 minute)
1. Navigate to /ui/requests
2. Show requests table
3. Update status using dropdown
4. Show HTMX update (no page reload)
5. Create payment for completed request

### Step 4: API Demo (1 minute)
1. Open http://localhost:8000/docs
2. Show Swagger UI
3. Test GET /providers?area_id=1&category_id=1
4. Show response with provider data

### Step 5: Key Features (30 seconds)
1. Highlight HTMX dynamic updates
2. Show Bootstrap responsive design
3. Show error handling (try duplicate email)
4. Show validation (try invalid review)

### Total Time: ~5 minutes

## Technical Decisions

1. **HTMX over React:** Simpler, no build step, server-rendered
2. **Jinja2 templates:** Server-side rendering, easy to maintain
3. **Bootstrap 5:** Quick styling, responsive out of the box
4. **SQLAlchemy ORM:** Type safety, relationship management
5. **Pydantic schemas:** Request/response validation
6. **ENUM types:** Database-level validation for status fields
7. **CASCADE deletes:** Maintain referential integrity automatically

