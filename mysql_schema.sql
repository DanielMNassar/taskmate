-- MySQL Schema for Home Service Management System
-- Converted from PostgreSQL with full constraint enforcement

-- Drop tables in reverse dependency order (if needed for clean setup)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS service_request;
DROP TABLE IF EXISTS provider_category;
DROP TABLE IF EXISTS service_provider;
DROP TABLE IF EXISTS service_category;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS service_area;
SET FOREIGN_KEY_CHECKS = 1;

-- SERVICE_AREA (independent entity, referenced by others)
CREATE TABLE service_area (
    area_id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    UNIQUE KEY uk_area_location (city, district, postal_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SERVICE_CATEGORY (independent entity)
CREATE TABLE service_category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- CUSTOMER (references service_area)
CREATE TABLE customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(30) NOT NULL,
    address VARCHAR(255) NOT NULL,
    area_id INT,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_area
        FOREIGN KEY (area_id) REFERENCES service_area(area_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SERVICE_PROVIDER (references service_area)
CREATE TABLE service_provider (
    provider_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(30) NOT NULL,
    address VARCHAR(255) NOT NULL,
    area_id INT,
    hourly_rate DECIMAL(10,2) NOT NULL CHECK (hourly_rate >= 0),
    availability_status ENUM('available', 'busy', 'unavailable') DEFAULT 'available',
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_provider_area
        FOREIGN KEY (area_id) REFERENCES service_area(area_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PROVIDER_CATEGORY (many-to-many intersection table)
CREATE TABLE provider_category (
    provider_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (provider_id, category_id),
    CONSTRAINT fk_pc_provider
        FOREIGN KEY (provider_id) REFERENCES service_provider(provider_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_pc_category
        FOREIGN KEY (category_id) REFERENCES service_category(category_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SERVICE_REQUEST (references customer, provider, category, area)
CREATE TABLE service_request (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    provider_id INT,
    category_id INT NOT NULL,
    area_id INT NOT NULL,
    address VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('pending', 'accepted', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    cost DECIMAL(10,2) CHECK (cost >= 0),
    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    cancellation_date DATETIME NULL,
    CONSTRAINT fk_req_customer
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_req_provider
        FOREIGN KEY (provider_id) REFERENCES service_provider(provider_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_req_category
        FOREIGN KEY (category_id) REFERENCES service_category(category_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_req_area
        FOREIGN KEY (area_id) REFERENCES service_area(area_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PAYMENT (one-to-one with service_request)
CREATE TABLE payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    payment_method ENUM('credit_card', 'debit_card', 'cash', 'paypal', 'bank_transfer') NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    payment_status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    CONSTRAINT fk_payment_request
        FOREIGN KEY (request_id) REFERENCES service_request(request_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- REVIEW (one-to-many with service_request)
CREATE TABLE review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    customer_id INT NOT NULL,
    provider_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_request
        FOREIGN KEY (request_id) REFERENCES service_request(request_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_review_customer
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_review_provider
        FOREIGN KEY (provider_id) REFERENCES service_provider(provider_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY uk_review_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

